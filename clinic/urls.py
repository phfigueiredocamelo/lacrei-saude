"""Clinic API routes."""

from django.urls import path

from clinic import views

urlpatterns = [
    path("health/", views.healthcheck, name="healthcheck"),
]
