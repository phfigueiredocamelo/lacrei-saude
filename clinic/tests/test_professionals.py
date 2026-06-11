from django.test import TestCase

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
