"""Public API views."""

import logging

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import (
    action,
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from clinic.asaas import (
    AsaasError,
    create_payment_for_appointment,
    map_asaas_event_to_status,
)
from clinic.models import Appointment, Professional
from clinic.serializers import AppointmentSerializer, ProfessionalSerializer

logger = logging.getLogger(__name__)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def healthcheck(request):
    return Response({"status": "ok"})


def payment_info(appointment):
    return {
        "payment_status": appointment.payment_status,
        "asaas_payment_id": appointment.asaas_payment_id,
        "asaas_customer_id": appointment.asaas_customer_id,
        "external_reference": appointment.external_reference,
    }


@api_view(["POST"])
def asaas_webhook(request):
    event = request.data.get("event")
    payment = request.data.get("payment") or {}
    payment_id = payment.get("id") if isinstance(payment, dict) else None
    external_reference = (
        payment.get("externalReference") if isinstance(payment, dict) else None
    )
    status_value = map_asaas_event_to_status(event)

    if not event or not payment_id or status_value is None:
        return Response({"status": "ignored"})

    appointments = Appointment.objects.filter(asaas_payment_id=payment_id)
    if external_reference:
        if not external_reference.startswith("appointment:"):
            return Response({"status": "ignored"})
        try:
            appointment_id = int(external_reference.removeprefix("appointment:"))
        except (AttributeError, ValueError):
            return Response({"status": "ignored"})
        appointments = appointments.filter(id=appointment_id)

    updated = appointments.update(
        payment_status=status_value,
        updated_at=timezone.now(),
    )
    if not updated:
        return Response({"status": "ignored"})

    return Response({"status": "processed", "updated": updated})


class ProfessionalViewSet(viewsets.ModelViewSet):
    queryset = Professional.objects.all()
    serializer_class = ProfessionalSerializer
    filterset_fields = ["slug", "profession"]

    def perform_create(self, serializer):
        try:
            professional = serializer.save()
        except Exception as exc:
            logger.error(
                "professional_create_failed error_type=%s error_message=%s "
                "payload_keys=%s slug=%s",
                exc.__class__.__name__,
                str(exc),
                sorted(self.request.data.keys()),
                serializer.validated_data.get("slug"),
            )
            raise

        logger.info(
            "professional_created professional_id=%s slug=%s",
            professional.id,
            professional.slug,
        )

    @action(detail=True, methods=["get"], url_path="appointments")
    def appointments(self, request, pk=None):
        professional = self.get_object()
        appointments = Appointment.objects.filter(professional=professional)
        page = self.paginate_queryset(appointments)
        if page is not None:
            serializer = AppointmentSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = AppointmentSerializer(appointments, many=True)
        return Response(serializer.data)


class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.select_related("professional").all()
    serializer_class = AppointmentSerializer
    filterset_fields = ["professional", "payment_status"]

    @action(detail=True, methods=["get", "post"], url_path="payment")
    def payment(self, request, pk=None):
        appointment = self.get_object()

        if request.method == "GET":
            return Response(payment_info(appointment))

        try:
            appointment = create_payment_for_appointment(appointment)
        except ValueError as exc:
            return Response(
                {"asaas_customer_id": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except AsaasError:
            return Response(
                {"detail": "Failed to create payment."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(payment_info(appointment))
