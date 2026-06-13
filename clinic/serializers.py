from decimal import Decimal, InvalidOperation

import bleach
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import serializers

from clinic.asaas import AsaasClient, AsaasError
from clinic.models import Appointment, Patient, Professional


def clean_text(value):
    return bleach.clean(value.strip(), tags=[], attributes={}, strip=True)


class ProfessionalSerializer(serializers.ModelSerializer):
    slug = serializers.SlugField(
        allow_blank=True,
        max_length=170,
        required=False,
    )

    class Meta:
        model = Professional
        fields = [
            "id",
            "social_name",
            "slug",
            "profession",
            "address",
            "contact",
            "is_active",
            "created_at",
            "updated_at",
            "deleted_at",
        ]
        read_only_fields = [
            "id",
            "is_active",
            "created_at",
            "updated_at",
            "deleted_at",
        ]

    def validate(self, attrs):
        text_fields = ["social_name", "profession", "address", "contact"]
        errors = {}

        for field in text_fields:
            if field in attrs:
                attrs[field] = clean_text(attrs[field])
                if not attrs[field]:
                    errors[field] = "This field may not be blank."

        should_validate_slug = (
            self.instance is None or "slug" in attrs or "social_name" in attrs
        )
        if should_validate_slug:
            slug_source = clean_text(attrs.get("slug", "")) or attrs.get(
                "social_name",
                getattr(self.instance, "social_name", ""),
            )
            attrs["slug"] = slugify(slug_source)
            if not attrs["slug"]:
                errors["slug"] = "This field may not be blank."
            else:
                duplicate_slug = Professional.all_objects.filter(slug=attrs["slug"])
                if self.instance is not None:
                    duplicate_slug = duplicate_slug.exclude(pk=self.instance.pk)
                if duplicate_slug.exists():
                    errors["slug"] = "professional with this slug already exists."

        if errors:
            raise serializers.ValidationError(errors)

        return attrs


class AppointmentSerializer(serializers.ModelSerializer):
    professional = serializers.PrimaryKeyRelatedField(
        queryset=Professional.objects.all(),
    )
    asaas_split = serializers.JSONField(required=False)

    class Meta:
        model = Appointment
        fields = [
            "id",
            "date",
            "professional",
            "patient",
            "customer_name",
            "customer_document",
            "price",
            "payment_status",
            "asaas_payment_id",
            "asaas_customer_id",
            "asaas_split",
            "is_active",
            "created_at",
            "updated_at",
            "deleted_at",
        ]
        read_only_fields = [
            "id",
            "patient",
            "payment_status",
            "asaas_payment_id",
            "asaas_customer_id",
            "is_active",
            "created_at",
            "updated_at",
            "deleted_at",
        ]

    def validate(self, attrs):
        errors = {}

        if "customer_name" in attrs:
            attrs["customer_name"] = clean_text(attrs["customer_name"])
            if not attrs["customer_name"]:
                errors["customer_name"] = "This field may not be blank."

        if "customer_document" in attrs:
            attrs["customer_document"] = clean_text(attrs["customer_document"])
            if not attrs["customer_document"]:
                errors["customer_document"] = "This field may not be blank."

        if attrs.get("date") and attrs["date"] < timezone.now():
            errors["date"] = "Appointment date cannot be in the past."

        if attrs.get("price") is not None and attrs["price"] <= Decimal("0"):
            errors["price"] = "Price must be greater than zero."

        professional = attrs.get(
            "professional",
            getattr(self.instance, "professional", None),
        )
        professional_is_active = (
            professional is not None
            and Professional.all_objects.filter(
                pk=professional.pk, is_active=True
            ).exists()
        )
        if professional is not None and not professional_is_active:
            errors["professional"] = "Professional must be active."

        split_errors = self._validate_asaas_split(attrs.get("asaas_split", []))
        if split_errors:
            errors["asaas_split"] = split_errors

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    def create(self, validated_data):
        patient = self._get_or_create_patient(validated_data)
        self._sync_asaas_customer(patient, validated_data)
        validated_data["patient"] = patient
        validated_data["asaas_customer_id"] = patient.asaas_id
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "customer_document" in validated_data or "customer_name" in validated_data:
            patient_data = {
                "customer_document": validated_data.get(
                    "customer_document",
                    instance.customer_document,
                ),
                "customer_name": validated_data.get(
                    "customer_name",
                    instance.customer_name,
                ),
            }
            validated_data["patient"] = self._get_or_create_patient(patient_data)
            self._sync_asaas_customer(validated_data["patient"], patient_data)
            validated_data["asaas_customer_id"] = validated_data["patient"].asaas_id
        return super().update(instance, validated_data)

    def _get_or_create_patient(self, data):
        document = data.get("customer_document")
        name = data.get("customer_name")
        patient, _ = Patient.objects.get_or_create(
            document=document,
            defaults={"name": name},
        )
        if patient.name != name:
            patient.name = name
            patient.save(update_fields=["name", "updated_at"])
        return patient

    def _sync_asaas_customer(self, patient, data):
        payload = {
            "name": data.get("customer_name"),
            "cpfCnpj": data.get("customer_document"),
        }
        client = AsaasClient()
        try:
            if patient.asaas_id:
                client.update_customer(patient.asaas_id, payload)
                return

            result = client.create_customer(payload)
        except AsaasError as exc:
            raise serializers.ValidationError(
                {"asaas_customer_id": "Failed to sync Asaas customer."}
            ) from exc

        customer_id = result.get("id")
        if not customer_id:
            raise serializers.ValidationError(
                {"asaas_customer_id": "Asaas response did not include customer id."}
            )

        patient.asaas_id = customer_id
        patient.save(update_fields=["asaas_id", "updated_at"])

    def _validate_asaas_split(self, split):
        if split in (None, ""):
            return "Asaas split must be a list."

        if not isinstance(split, list):
            return "Asaas split must be a list."

        errors = []
        total_percentual = Decimal("0")

        for index, item in enumerate(split):
            if not isinstance(item, dict):
                errors.append(f"Item {index} must be an object.")
                continue

            raw_wallet_id = item.get("walletId")
            wallet_id = (
                clean_text(raw_wallet_id) if isinstance(raw_wallet_id, str) else ""
            )
            if not wallet_id:
                errors.append(f"Item {index} walletId is required.")
            else:
                item["walletId"] = wallet_id

            has_fixed = self._has_split_value(item, "fixedValue")
            has_percentual = self._has_split_value(item, "percentualValue")
            if has_fixed == has_percentual:
                errors.append(
                    f"Item {index} must include exactly one of fixedValue "
                    "or percentualValue."
                )
                continue

            if has_fixed:
                fixed_value = self._to_decimal(item["fixedValue"])
                if fixed_value is None or fixed_value <= Decimal("0"):
                    errors.append(f"Item {index} fixedValue must be positive.")

            if has_percentual:
                percentual_value = self._to_decimal(item["percentualValue"])
                if percentual_value is None or percentual_value <= Decimal("0"):
                    errors.append(f"Item {index} percentualValue must be positive.")
                elif percentual_value > Decimal("100"):
                    errors.append(
                        f"Item {index} percentualValue must be less than or "
                        "equal to 100."
                    )
                else:
                    total_percentual += percentual_value

        if total_percentual > Decimal("100"):
            errors.append("Total percentualValue cannot exceed 100.")

        return errors

    def _has_split_value(self, item, field):
        return field in item and item[field] not in (None, "")

    def _to_decimal(self, value):
        try:
            decimal_value = Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None
        if not decimal_value.is_finite():
            return None
        return decimal_value
