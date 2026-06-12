"""URL configuration for the Lacrei Saude API."""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny


class PublicSpectacularAPIView(SpectacularAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]


class PublicSpectacularSwaggerView(SpectacularSwaggerView):
    authentication_classes = []
    permission_classes = [AllowAny]


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("clinic.urls")),
    path(
        "api/schema/",
        PublicSpectacularAPIView.as_view(),
        name="schema",
    ),
    path(
        "api/docs/",
        PublicSpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
