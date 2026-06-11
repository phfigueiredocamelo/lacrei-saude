"""Clinic API routes."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from clinic import views

router = DefaultRouter()
router.register("professionals", views.ProfessionalViewSet, basename="professional")
router.register("appointments", views.AppointmentViewSet, basename="appointment")

urlpatterns = [
    path("health/", views.healthcheck, name="healthcheck"),
    path("api/", include(router.urls)),
]
