"""Asaas payment integration helpers."""

from json import JSONDecodeError
from typing import Any

import requests
from django.conf import settings

from clinic.models import Appointment


class AsaasError(Exception):
    """Raised when Asaas rejects or fails a payment request."""


class AsaasClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: int = 15,
    ):
        self.base_url = (base_url or settings.ASAAS_BASE_URL).rstrip("/")
        self.api_key = api_key or settings.ASAAS_API_KEY
        self.timeout = timeout

    def create_payment(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("post", "/v3/lean/payments", payload)

    def create_customer(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("post", "/v3/customers", payload)

    def update_customer(
        self,
        customer_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return self._request("put", f"/v3/customers/{customer_id}", payload)

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            response = getattr(requests, method)(
                f"{self.base_url}{path}",
                json=payload,
                headers={
                    "accept": "application/json",
                    "content-type": "application/json",
                    "access_token": self.api_key,
                },
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise AsaasError("Asaas request failed.") from exc

        if response.status_code >= 400:
            raise AsaasError(response.text)
        try:
            return response.json()
        except (JSONDecodeError, ValueError) as exc:
            raise AsaasError("Asaas response was not valid JSON.") from exc


def build_payment_payload(appointment: Appointment) -> dict[str, Any]:
    return {
        "customer": appointment.asaas_customer_id,
        "billingType": settings.ASAAS_DEFAULT_BILLING_TYPE,
        "value": float(appointment.price),
        "dueDate": appointment.date.date().isoformat(),
        "externalReference": appointment.external_reference,
        "split": appointment.asaas_split,
    }


def build_customer_payload(appointment: Appointment) -> dict[str, Any]:
    return {
        "name": appointment.customer_name,
        "cpfCnpj": appointment.customer_document,
    }


def ensure_asaas_customer(
    appointment: Appointment,
    client: AsaasClient,
) -> Appointment:
    if appointment.asaas_customer_id:
        return appointment

    raise ValueError("asaas_customer_id is required to create a payment.")


def create_payment_for_appointment(
    appointment: Appointment,
    client: AsaasClient | None = None,
) -> Appointment:
    payment_client = client or AsaasClient()
    appointment = ensure_asaas_customer(appointment, payment_client)
    result = payment_client.create_payment(build_payment_payload(appointment))
    payment_id = result.get("id")
    if not payment_id:
        raise AsaasError("Asaas response did not include payment id.")

    appointment.asaas_payment_id = payment_id
    appointment.payment_status = Appointment.PaymentStatus.CREATED
    appointment.save(update_fields=["asaas_payment_id", "payment_status", "updated_at"])
    return appointment


def map_asaas_event_to_status(event: str) -> str | None:
    status_map = {
        "PAYMENT_RECEIVED": Appointment.PaymentStatus.PAID,
        "PAYMENT_CONFIRMED": Appointment.PaymentStatus.PAID,
        "PAYMENT_OVERDUE": Appointment.PaymentStatus.FAILED,
        "PAYMENT_DELETED": Appointment.PaymentStatus.CANCELED,
    }
    return status_map.get(event)
