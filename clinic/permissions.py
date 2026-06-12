"""Custom DRF permissions for the clinic API."""

from dataclasses import dataclass
from secrets import compare_digest

from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission


@dataclass(frozen=True)
class APIKeyPrincipal:
    """Minimal authenticated principal for API-key requests."""

    is_authenticated: bool = True
    username: str = "api-key"


class APIKeyAuthentication(BaseAuthentication):
    """Authenticate requests with the X-API-Key header."""

    keyword = "X-API-Key"
    message = "Invalid or missing API key."

    def authenticate(self, request):
        expected_key = settings.API_KEY
        provided_key = request.headers.get(self.keyword)
        if expected_key and provided_key and compare_digest(provided_key, expected_key):
            return (APIKeyPrincipal(), provided_key)

        raise AuthenticationFailed(self.message)

    def authenticate_header(self, request):
        return self.keyword


class HasAPIKey(BasePermission):
    """Require a matching API key in the X-API-Key header."""

    message = "Invalid or missing API key."

    def has_permission(self, request, view) -> bool:
        return isinstance(request.successful_authenticator, APIKeyAuthentication)
