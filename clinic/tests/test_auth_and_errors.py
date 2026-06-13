from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase


@override_settings(API_KEY="test-key")
class APIKeyAuthAndErrorTests(APITestCase):
    def test_missing_api_key_returns_401(self):
        with self.assertLogs("clinic.exceptions", level="WARNING") as logs:
            response = self.client.get("/api/professionals/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["detail"], "Invalid or missing API key.")
        self.assertIn("api_error", logs.output[0])
        self.assertIn("status_code=401", logs.output[0])
        self.assertIn("method=GET", logs.output[0])
        self.assertIn("path=/api/professionals/", logs.output[0])

    def test_invalid_api_key_returns_401(self):
        self.client.credentials(HTTP_X_API_KEY="wrong-key")

        response = self.client.get("/api/professionals/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_professional_payload_returns_400_with_social_name_error(self):
        self.client.credentials(HTTP_X_API_KEY="test-key")

        with self.assertLogs("clinic.exceptions", level="WARNING") as logs:
            response = self.client.post(
                "/api/professionals/",
                {
                    "social_name": "   ",
                    "profession": "Psicologia",
                    "address": "Rua Um",
                    "contact": "ana@example.com",
                },
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("social_name", response.data)
        self.assertIn("api_error", logs.output[0])
        self.assertIn("status_code=400", logs.output[0])
        self.assertIn("method=POST", logs.output[0])
        self.assertIn("path=/api/professionals/", logs.output[0])

    def test_healthcheck_is_public(self):
        response = self.client.get("/health/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"status": "ok"})

    def test_openapi_schema_is_public(self):
        response = self.client.get("/api/schema/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_swagger_ui_is_public(self):
        response = self.client.get("/api/docs/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
