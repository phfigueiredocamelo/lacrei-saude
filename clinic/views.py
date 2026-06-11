"""Public API views."""

from rest_framework import viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from clinic.models import Appointment, Professional
from clinic.serializers import AppointmentSerializer, ProfessionalSerializer


@api_view(["GET"])
@permission_classes([AllowAny])
def healthcheck(request):
    return Response({"status": "ok"})


class ProfessionalViewSet(viewsets.ModelViewSet):
    queryset = Professional.objects.all()
    serializer_class = ProfessionalSerializer
    filterset_fields = ["slug", "profession"]

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
