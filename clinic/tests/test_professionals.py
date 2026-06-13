from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from clinic.models import Professional
from clinic.serializers import ProfessionalSerializer


class ProfessionalSerializerTests(TestCase):
    def test_generates_slug_when_missing(self):
        serializer = ProfessionalSerializer(
            data={
                "social_name": "  Dra. Ana <strong>Silva</strong>  ",
                "profession": "  Psicologia  ",
                "address": "  Rua das Flores, 123  ",
                "contact": "  ana@example.com  ",
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

        self.assertEqual(serializer.validated_data["social_name"], "Dra. Ana Silva")
        self.assertEqual(serializer.validated_data["slug"], "dra-ana-silva")

    def test_rejects_duplicate_slug(self):
        Professional.objects.create(
            social_name="Dra. Ana Silva",
            slug="dra-ana-silva",
            profession="Psicologia",
            address="Rua das Flores, 123",
            contact="ana@example.com",
        )

        serializer = ProfessionalSerializer(
            data={
                "social_name": "Dra. Ana Silva",
                "slug": "dra-ana-silva",
                "profession": "Psicologia",
                "address": "Rua das Flores, 123",
                "contact": "ana@example.com",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("slug", serializer.errors)

    def test_partial_update_keeps_existing_slug(self):
        professional = Professional.objects.create(
            social_name="Dra. Ana Silva",
            slug="dra-ana-silva",
            profession="Psicologia",
            address="Rua das Flores, 123",
            contact="ana@example.com",
        )

        serializer = ProfessionalSerializer(
            professional,
            data={"contact": " nova@example.com "},
            partial=True,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        self.assertEqual(updated.slug, "dra-ana-silva")
        self.assertEqual(updated.contact, "nova@example.com")


@override_settings(API_KEY="test-key")
class ProfessionalAPITests(APITestCase):
    def setUp(self):
        self.client.credentials(HTTP_X_API_KEY="test-key")

    def test_create_list_retrieve_update_and_soft_delete_professional(self):
        create_response = self.client.post(
            "/api/professionals/",
            {
                "social_name": "Dra Clara",
                "profession": "Clinica Geral",
                "address": "Rua Um, 10",
                "contact": "clara@example.com",
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        professional_id = create_response.data["id"]
        self.assertEqual(create_response.data["slug"], "dra-clara")

        list_response = self.client.get("/api/professionals/")
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data["count"], 1)

        detail_response = self.client.get(f"/api/professionals/{professional_id}/")
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["social_name"], "Dra Clara")

        update_response = self.client.patch(
            f"/api/professionals/{professional_id}/",
            {"contact": "nova@example.com"},
            format="json",
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data["contact"], "nova@example.com")

        delete_response = self.client.delete(f"/api/professionals/{professional_id}/")
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        deleted_professional = Professional.all_objects.get(pk=professional_id)
        self.assertFalse(deleted_professional.is_active)
        self.assertIsNotNone(deleted_professional.deleted_at)

        hidden_response = self.client.get(f"/api/professionals/{professional_id}/")
        self.assertEqual(hidden_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_filter_by_slug(self):
        Professional.objects.create(
            social_name="Dra Alpha",
            slug="dra-alpha",
            profession="Psicologia",
            address="Rua Um",
            contact="alpha@example.com",
        )
        Professional.objects.create(
            social_name="Dra Beta",
            slug="dra-beta",
            profession="Psiquiatria",
            address="Rua Dois",
            contact="beta@example.com",
        )

        response = self.client.get("/api/professionals/?slug=dra-beta")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["slug"], "dra-beta")

    def test_unexpected_create_error_is_logged_with_context(self):
        self.client.raise_request_exception = False

        with (
            self.assertLogs("clinic.views", level="ERROR") as logs,
            patch.object(
                ProfessionalSerializer,
                "save",
                side_effect=RuntimeError("database exploded"),
            ),
        ):
            response = self.client.post(
                "/api/professionals/",
                {
                    "social_name": "Dra Clara",
                    "profession": "Clinica Geral",
                    "address": "Rua Um, 10",
                    "contact": "clara@example.com",
                },
                format="json",
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
        self.assertIn("professional_create_failed", logs.output[0])
        self.assertIn("payload_keys=", logs.output[0])
        self.assertIn("slug=dra-clara", logs.output[0])
