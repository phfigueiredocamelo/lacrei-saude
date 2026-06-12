from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from clinic.models import Appointment, Professional
from clinic.serializers import AppointmentSerializer


class AppointmentSerializerTests(TestCase):
    def setUp(self):
        self.professional = Professional.objects.create(
            social_name="Dra. Ana Silva",
            slug="dra-ana-silva",
            profession="Psicologia",
            address="Rua das Flores, 123",
            contact="ana@example.com",
        )

    def valid_data(self, **overrides):
        data = {
            "date": (timezone.now() + timezone.timedelta(days=1)).isoformat(),
            "professional": self.professional.id,
            "customer_name": "  Maria <b>Oliveira</b>  ",
            "customer_document": "  123.456.789-00  ",
            "price": "150.00",
            "asaas_split": [
                {"walletId": "wallet-fixed", "fixedValue": "50.00"},
                {"walletId": "wallet-percent", "percentualValue": "20"},
            ],
        }
        data.update(overrides)
        return data

    def test_accepts_valid_appointment(self):
        serializer = AppointmentSerializer(data=self.valid_data())

        self.assertTrue(serializer.is_valid(), serializer.errors)

        self.assertEqual(serializer.validated_data["professional"], self.professional)
        self.assertEqual(serializer.validated_data["customer_name"], "Maria Oliveira")
        self.assertEqual(
            serializer.validated_data["customer_document"], "123.456.789-00"
        )
        self.assertEqual(serializer.validated_data["price"], Decimal("150.00"))

    def test_sanitizes_split_wallet_id(self):
        serializer = AppointmentSerializer(
            data=self.valid_data(
                asaas_split=[
                    {"walletId": " <b>wallet-clean</b> ", "percentualValue": "20"}
                ]
            )
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(
            serializer.validated_data["asaas_split"][0]["walletId"],
            "wallet-clean",
        )

    def test_rejects_past_date(self):
        serializer = AppointmentSerializer(
            data=self.valid_data(
                date=(timezone.now() - timezone.timedelta(days=1)).isoformat()
            )
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("date", serializer.errors)

    def test_rejects_inactive_professional(self):
        inactive_professional = Professional.all_objects.create(
            social_name="Dr. Carlos Lima",
            slug="dr-carlos-lima",
            profession="Psiquiatria",
            address="Av. Brasil, 456",
            contact="carlos@example.com",
            is_active=False,
            deleted_at=timezone.now(),
        )

        serializer = AppointmentSerializer(
            data=self.valid_data(professional=inactive_professional.id)
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("professional", serializer.errors)

    def test_partial_update_rejects_existing_inactive_professional(self):
        appointment = AppointmentSerializer(data=self.valid_data())
        self.assertTrue(appointment.is_valid(), appointment.errors)
        instance = appointment.save()
        self.professional.delete()

        serializer = AppointmentSerializer(
            instance,
            data={"customer_name": "Maria Atualizada"},
            partial=True,
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("professional", serializer.errors)

    def test_rejects_split_item_with_fixed_and_percentual_values(self):
        serializer = AppointmentSerializer(
            data=self.valid_data(
                asaas_split=[
                    {
                        "walletId": "wallet-invalid",
                        "fixedValue": "10.00",
                        "percentualValue": "15",
                    }
                ]
            )
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("asaas_split", serializer.errors)

    def test_rejects_null_wallet_id(self):
        serializer = AppointmentSerializer(
            data=self.valid_data(
                asaas_split=[{"walletId": None, "percentualValue": "15"}]
            )
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("asaas_split", serializer.errors)

    def test_rejects_non_finite_split_value(self):
        serializer = AppointmentSerializer(
            data=self.valid_data(
                asaas_split=[{"walletId": "wallet-invalid", "percentualValue": "NaN"}]
            )
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("asaas_split", serializer.errors)


@override_settings(API_KEY="test-key")
class AppointmentAPITests(APITestCase):
    def setUp(self):
        self.client.credentials(HTTP_X_API_KEY="test-key")
        self.professional = Professional.objects.create(
            social_name="Dra. Ana Silva",
            slug="dra-ana-api",
            profession="Psicologia",
            address="Rua das Flores, 123",
            contact="ana@example.com",
        )

    def appointment_payload(self, **overrides):
        payload = {
            "date": (timezone.now() + timezone.timedelta(days=1)).isoformat(),
            "professional": self.professional.id,
            "customer_name": "Maria Oliveira",
            "customer_document": "123.456.789-00",
            "price": "150.00",
            "asaas_split": [
                {"walletId": "wallet-fixed", "fixedValue": "50.00"},
                {"walletId": "wallet-percent", "percentualValue": "20"},
            ],
        }
        payload.update(overrides)
        return payload

    def test_create_list_retrieve_update_and_soft_delete_appointment(self):
        create_response = self.client.post(
            "/api/appointments/",
            self.appointment_payload(),
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        appointment_id = create_response.data["id"]
        self.assertEqual(create_response.data["customer_name"], "Maria Oliveira")
        self.assertEqual(create_response.data["customer_document"], "123.456.789-00")
        self.assertEqual(create_response.data["price"], "150.00")
        self.assertEqual(
            create_response.data["asaas_split"][0]["walletId"],
            "wallet-fixed",
        )
        self.assertEqual(create_response.data["professional"], self.professional.id)

        list_response = self.client.get("/api/appointments/")
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data["count"], 1)
        self.assertEqual(list_response.data["results"][0]["id"], appointment_id)

        detail_response = self.client.get(f"/api/appointments/{appointment_id}/")
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["professional"], self.professional.id)

        update_response = self.client.patch(
            f"/api/appointments/{appointment_id}/",
            {"customer_name": "Maria Atualizada", "price": "175.00"},
            format="json",
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data["customer_name"], "Maria Atualizada")
        self.assertEqual(update_response.data["price"], "175.00")

        delete_response = self.client.delete(f"/api/appointments/{appointment_id}/")
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        deleted_appointment = Appointment.all_objects.get(pk=appointment_id)
        self.assertFalse(deleted_appointment.is_active)
        self.assertIsNotNone(deleted_appointment.deleted_at)

        hidden_response = self.client.get(f"/api/appointments/{appointment_id}/")
        self.assertEqual(hidden_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_search_appointments_by_professional_id(self):
        other_professional = Professional.objects.create(
            social_name="Dr. Bruno Lima",
            slug="dr-bruno-api",
            profession="Psiquiatria",
            address="Av. Brasil, 456",
            contact="bruno@example.com",
        )
        Appointment.objects.create(
            date=timezone.now() + timezone.timedelta(days=1),
            professional=self.professional,
            customer_name="Maria Oliveira",
            customer_document="123.456.789-00",
            price=Decimal("150.00"),
            asaas_split=[{"walletId": "wallet-fixed", "fixedValue": "50.00"}],
        )
        Appointment.objects.create(
            date=timezone.now() + timezone.timedelta(days=2),
            professional=other_professional,
            customer_name="Joao Souza",
            customer_document="987.654.321-00",
            price=Decimal("200.00"),
            asaas_split=[{"walletId": "wallet-percent", "percentualValue": "20"}],
        )

        response = self.client.get(
            f"/api/professionals/{self.professional.id}/appointments/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["professional"],
            self.professional.id,
        )
