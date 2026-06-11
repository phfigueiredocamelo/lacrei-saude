from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from clinic.models import Professional
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
        self.assertEqual(serializer.validated_data["customer_document"], "123.456.789-00")
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
