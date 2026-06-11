"""Custom DRF permissions for the clinic API."""

from django.conf import settings
from rest_framework.permissions import BasePermission


class HasAPIKey(BasePermission):
    """Require a matching API key in the X-API-Key header."""

    message = "Invalid or missing API key."

    def has_permission(self, request, view) -> bool:
        if getattr(view, "allow_unauthenticated", False):
            return True

        expected_key = settings.API_KEY
        provided_key = request.headers.get("X-API-Key")
        return bool(expected_key and provided_key == expected_key)
