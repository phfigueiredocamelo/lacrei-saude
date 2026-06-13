from decimal import Decimal
from unittest.mock import Mock, patch

from django.test import override_settings
from django.utils import timezone
from requests import Timeout
from rest_framework import status
from rest_framework.test import APITestCase

from clinic.asaas import AsaasClient, AsaasError, create_payment_for_appointment
from clinic.models import Appointment, Patient, Professional


@override_settings(API_KEY="test-key", ASAAS_DEFAULT_BILLING_TYPE="BOLETO")
class PaymentAPITests(APITestCase):
    def setUp(self):
        self.client.credentials(HTTP_X_API_KEY="test-key")
        self.professional = Professional.objects.create(
            social_name="Dra. Ana Silva",
            slug="dra-ana-payments",
            profession="Psicologia",
            address="Rua das Flores, 123",
            contact="ana@example.com",
        )
        self.patient = Patient.objects.create(
            name="Maria Oliveira",
            document="123.456.789-00",
            asaas_id="cus_123",
        )
        self.appointment = Appointment.objects.create(
            date=timezone.now() + timezone.timedelta(days=1),
            professional=self.professional,
            patient=self.patient,
            customer_name="Maria Oliveira",
            customer_document="123.456.789-00",
            price=Decimal("300.00"),
            asaas_customer_id="cus_123",
            asaas_split=[{"walletId": "wallet_1", "percentualValue": 25}],
        )

    @patch("clinic.asaas.AsaasClient.create_payment")
    def test_create_payment_sends_payload_and_stores_payment(self, create_payment):
        create_payment.return_value = {"id": "pay_123", "status": "PENDING"}

        response = self.client.post(
            f"/api/appointments/{self.appointment.id}/payment/",
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["asaas_payment_id"], "pay_123")
        self.assertEqual(response.data["payment_status"], "CREATED")

        payload = create_payment.call_args.args[0]
        self.assertEqual(payload["customer"], "cus_123")
        self.assertEqual(payload["billingType"], "BOLETO")
        self.assertEqual(payload["value"], 300.0)
        self.assertEqual(payload["dueDate"], self.appointment.date.date().isoformat())
        self.assertEqual(
            payload["externalReference"],
            f"appointment:{self.appointment.id}",
        )
        self.assertEqual(
            payload["split"],
            [{"walletId": "wallet_1", "percentualValue": 25}],
        )

    def test_create_payment_requires_asaas_customer_id(self):
        self.appointment.asaas_customer_id = ""
        self.appointment.save(update_fields=["asaas_customer_id"])

        response = self.client.post(
            f"/api/appointments/{self.appointment.id}/payment/",
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("asaas_customer_id", response.data)

    @patch("clinic.serializers.AsaasClient.create_customer")
    def test_create_appointment_creates_patient_by_document(self, create_customer):
        create_customer.return_value = {"id": "cus_new"}

        response = self.client.post(
            "/api/appointments/",
            {
                "date": (timezone.now() + timezone.timedelta(days=2)).isoformat(),
                "professional": self.professional.id,
                "customer_name": "Joao Pessoa",
                "customer_document": "987.654.321-00",
                "price": "250.00",
                "asaas_split": [],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        patient = Patient.objects.get(document="987.654.321-00")
        self.assertEqual(patient.name, "Joao Pessoa")
        self.assertEqual(patient.asaas_id, "cus_new")
        appointment = Appointment.objects.get(id=response.data["id"])
        self.assertEqual(appointment.patient, patient)
        self.assertEqual(appointment.asaas_customer_id, "cus_new")
        create_customer.assert_called_once_with(
            {
                "name": "Joao Pessoa",
                "cpfCnpj": "987.654.321-00",
            }
        )

    @patch("clinic.serializers.AsaasClient.update_customer")
    @patch("clinic.serializers.AsaasClient.create_customer")
    def test_create_appointment_reuses_patient_by_document(
        self,
        create_customer,
        update_customer,
    ):
        patient = Patient.objects.create(
            name="Nome Antigo",
            document="987.654.321-00",
            asaas_id="cus_existing",
        )

        response = self.client.post(
            "/api/appointments/",
            {
                "date": (timezone.now() + timezone.timedelta(days=2)).isoformat(),
                "professional": self.professional.id,
                "customer_name": "Nome Novo",
                "customer_document": "987.654.321-00",
                "price": "250.00",
                "asaas_split": [],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        create_customer.assert_not_called()
        update_customer.assert_called_once_with(
            "cus_existing",
            {
                "name": "Nome Novo",
                "cpfCnpj": "987.654.321-00",
            },
        )
        patient.refresh_from_db()
        self.assertEqual(patient.name, "Nome Novo")
        self.assertEqual(patient.asaas_id, "cus_existing")
        appointment = Appointment.objects.get(id=response.data["id"])
        self.assertEqual(appointment.patient, patient)
        self.assertEqual(appointment.asaas_customer_id, "cus_existing")

    def test_get_payment_returns_payment_info(self):
        self.appointment.asaas_payment_id = "pay_123"
        self.appointment.payment_status = Appointment.PaymentStatus.CREATED
        self.appointment.save(update_fields=["asaas_payment_id", "payment_status"])

        response = self.client.get(f"/api/appointments/{self.appointment.id}/payment/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["payment_status"], "CREATED")
        self.assertEqual(response.data["asaas_payment_id"], "pay_123")
        self.assertEqual(response.data["asaas_customer_id"], "cus_123")
        self.assertEqual(
            response.data["external_reference"],
            f"appointment:{self.appointment.id}",
        )

    def test_asaas_webhook_payment_received_updates_appointment_status(self):
        self.appointment.asaas_payment_id = "pay_123"
        self.appointment.payment_status = Appointment.PaymentStatus.CREATED
        self.appointment.save(update_fields=["asaas_payment_id", "payment_status"])

        response = self.client.post(
            "/api/asaas/webhook/",
            {
                "event": "PAYMENT_RECEIVED",
                "payment": {
                    "id": "pay_123",
                    "externalReference": f"appointment:{self.appointment.id}",
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"status": "processed", "updated": 1})
        self.appointment.refresh_from_db()
        self.assertEqual(
            self.appointment.payment_status,
            Appointment.PaymentStatus.PAID,
        )

    def test_asaas_webhook_ignores_wrong_external_reference(self):
        self.appointment.asaas_payment_id = "pay_123"
        self.appointment.payment_status = Appointment.PaymentStatus.CREATED
        self.appointment.save(update_fields=["asaas_payment_id", "payment_status"])

        response = self.client.post(
            "/api/asaas/webhook/",
            {
                "event": "PAYMENT_RECEIVED",
                "payment": {
                    "id": "pay_123",
                    "externalReference": "appointment:9999",
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"status": "ignored"})
        self.appointment.refresh_from_db()
        self.assertEqual(
            self.appointment.payment_status,
            Appointment.PaymentStatus.CREATED,
        )

    def test_asaas_webhook_ignores_malformed_external_reference(self):
        self.appointment.asaas_payment_id = "pay_123"
        self.appointment.payment_status = Appointment.PaymentStatus.CREATED
        self.appointment.save(update_fields=["asaas_payment_id", "payment_status"])

        response = self.client.post(
            "/api/asaas/webhook/",
            {
                "event": "PAYMENT_RECEIVED",
                "payment": {
                    "id": "pay_123",
                    "externalReference": str(self.appointment.id),
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"status": "ignored"})
        self.appointment.refresh_from_db()
        self.assertEqual(
            self.appointment.payment_status,
            Appointment.PaymentStatus.CREATED,
        )

    @patch("clinic.asaas.requests.post")
    def test_asaas_client_posts_expected_request(self, post):
        response = Mock(status_code=200)
        response.json.return_value = {"id": "pay_123"}
        post.return_value = response

        result = AsaasClient(
            base_url="https://sandbox.asaas.com/api",
            api_key="secret",
        ).create_payment({"value": 300.0})

        self.assertEqual(result, {"id": "pay_123"})
        post.assert_called_once_with(
            "https://sandbox.asaas.com/api/v3/lean/payments",
            json={"value": 300.0},
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "access_token": "secret",
            },
            timeout=15,
        )

    @patch("clinic.asaas.requests.post")
    def test_asaas_client_posts_expected_customer_request(self, post):
        response = Mock(status_code=200)
        response.json.return_value = {"id": "cus_123"}
        post.return_value = response

        result = AsaasClient(
            base_url="https://sandbox.asaas.com/api",
            api_key="secret",
        ).create_customer({"name": "Maria Oliveira", "cpfCnpj": "12345678900"})

        self.assertEqual(result, {"id": "cus_123"})
        post.assert_called_once_with(
            "https://sandbox.asaas.com/api/v3/customers",
            json={"name": "Maria Oliveira", "cpfCnpj": "12345678900"},
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "access_token": "secret",
            },
            timeout=15,
        )

    @patch("clinic.asaas.requests.put")
    def test_asaas_client_puts_expected_customer_update_request(self, put):
        response = Mock(status_code=200)
        response.json.return_value = {"id": "cus_123"}
        put.return_value = response

        result = AsaasClient(
            base_url="https://sandbox.asaas.com/api",
            api_key="secret",
        ).update_customer("cus_123", {"name": "Maria Atualizada"})

        self.assertEqual(result, {"id": "cus_123"})
        put.assert_called_once_with(
            "https://sandbox.asaas.com/api/v3/customers/cus_123",
            json={"name": "Maria Atualizada"},
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "access_token": "secret",
            },
            timeout=15,
        )

    @patch("clinic.asaas.requests.post")
    def test_asaas_client_wraps_request_errors(self, post):
        post.side_effect = Timeout("timed out")

        with self.assertRaises(AsaasError):
            AsaasClient().create_payment({"value": 300.0})

    @patch("clinic.asaas.AsaasClient.create_payment")
    def test_create_payment_requires_returned_payment_id(self, create_payment):
        create_payment.return_value = {"status": "PENDING"}

        with self.assertRaises(AsaasError):
            create_payment_for_appointment(self.appointment)

        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.asaas_payment_id, "")
        self.assertEqual(
            self.appointment.payment_status,
            Appointment.PaymentStatus.PENDING,
        )
