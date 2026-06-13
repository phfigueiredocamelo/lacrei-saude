from django.contrib import admin

from clinic.models import Appointment, Patient, Professional


@admin.register(Professional)
class ProfessionalAdmin(admin.ModelAdmin):
    list_display = (
        "social_name",
        "profession",
        "contact",
        "is_active",
        "created_at",
    )
    search_fields = ("social_name", "slug", "profession", "contact")
    list_filter = ("is_active", "profession", "created_at")
    prepopulated_fields = {"slug": ("social_name",)}
    readonly_fields = ("created_at", "updated_at", "deleted_at")

    def get_queryset(self, request):
        return self.model.all_objects.all()


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "document",
        "asaas_id",
        "is_active",
        "created_at",
    )
    search_fields = ("name", "document", "asaas_id")
    list_filter = ("is_active", "created_at")
    readonly_fields = ("created_at", "updated_at", "deleted_at")

    def get_queryset(self, request):
        return self.model.all_objects.all()


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "professional",
        "patient",
        "customer_name",
        "price",
        "payment_status",
        "is_active",
    )
    search_fields = (
        "customer_name",
        "customer_document",
        "patient__name",
        "patient__document",
        "patient__asaas_id",
        "professional__social_name",
        "asaas_payment_id",
        "asaas_customer_id",
    )
    list_filter = ("payment_status", "is_active", "date", "created_at")
    readonly_fields = ("created_at", "updated_at", "deleted_at")
    autocomplete_fields = ("professional", "patient")

    def get_queryset(self, request):
        return self.model.all_objects.all()
