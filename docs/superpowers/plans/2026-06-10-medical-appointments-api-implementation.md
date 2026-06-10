# Medical Appointments API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-oriented but lean Django REST API for healthcare professionals, appointments, appointment-linked Asaas split payments, tests, Docker, Terraform, CI/CD, and documentation.

**Architecture:** A single Django project with one `clinic` app holds the API domain, serializers, viewsets, permissions, filters, Asaas client/service, and tests. Infrastructure and delivery are kept outside the app in Docker, GitHub Actions, and Terraform files. The API uses DRF JSON responses, PostgreSQL, API key authentication, soft delete, OpenAPI docs, and mocked payment calls in tests.

**Tech Stack:** Python 3.12, Django, Django REST Framework, PostgreSQL, Poetry, django-filter, django-cors-headers, drf-spectacular, bleach, requests, Gunicorn, Docker, Terraform, GitHub Actions, GCP Cloud Run, Cloud SQL, Artifact Registry, Secret Manager.

---

## File Structure

- Create `pyproject.toml`: Poetry metadata, dependencies, dev dependencies, Ruff/Black/Pytest config.
- Create `README.md`: setup, Docker, tests, API usage, CI/CD, GCP deploy, rollback, Asaas notes, decisions.
- Create `.env.example`: all required environment variables with safe example values.
- Create `.gitignore`: Python, Django, env, coverage, Terraform state, local artifacts.
- Create `manage.py`: Django command entrypoint.
- Create `config/__init__.py`: Django project package marker.
- Create `config/settings.py`: environment-driven settings for DRF, DB, CORS, security, logging, Swagger, API key.
- Create `config/urls.py`: routes for API, docs, schema, health.
- Create `config/asgi.py`: ASGI entrypoint.
- Create `config/wsgi.py`: WSGI entrypoint.
- Create `clinic/__init__.py`: app package marker.
- Create `clinic/apps.py`: Django app config.
- Create `clinic/models.py`: `Professional` and `Appointment`, soft delete helpers, slug generation.
- Create `clinic/serializers.py`: serializers and validation/sanitization.
- Create `clinic/permissions.py`: API key permission.
- Create `clinic/views.py`: viewsets, nested appointments route, payment endpoints, webhook, health.
- Create `clinic/urls.py`: DRF router and custom routes.
- Create `clinic/asaas.py`: Asaas client, payload builder, split validation, webhook status mapping.
- Create `clinic/admin.py`: basic admin registration.
- Create `clinic/migrations/__init__.py`: migrations package marker.
- Create `clinic/tests/__init__.py`: tests package marker.
- Create `clinic/tests/test_professionals.py`: professional API tests.
- Create `clinic/tests/test_appointments.py`: appointment API tests.
- Create `clinic/tests/test_auth_and_errors.py`: auth and invalid request tests.
- Create `clinic/tests/test_payments.py`: Asaas split/payment/webhook tests.
- Create `Dockerfile`: production image with Poetry install and Gunicorn.
- Create `docker-compose.yml`: API and PostgreSQL local stack.
- Create `.dockerignore`: image build exclusions.
- Create `.github/workflows/ci-cd.yml`: lint, tests, build, staging deploy, production deploy.
- Create `.github/workflows/rollback.yml`: manual Cloud Run rollback.
- Create `infra/terraform/main.tf`: providers and resource composition.
- Create `infra/terraform/variables.tf`: environment input variables.
- Create `infra/terraform/outputs.tf`: Cloud Run URLs and resource names.
- Create `infra/terraform/staging.tfvars.example`: staging variable example.
- Create `infra/terraform/production.tfvars.example`: production variable example.
- Create `docs/decisions-and-improvements.md`: errors found, decisions, and future improvements.

## Implementation Tasks

### Task 1: Project Skeleton And Dependencies

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `manage.py`
- Create: `config/__init__.py`
- Create: `config/asgi.py`
- Create: `config/wsgi.py`
- Create: `clinic/__init__.py`
- Create: `clinic/apps.py`

- [ ] **Step 1: Create the Poetry project metadata**

Add `pyproject.toml`:

```toml
[tool.poetry]
name = "lacrei-saude"
version = "0.1.0"
description = "REST API for healthcare professionals, appointments, and Asaas split payments"
authors = ["Lacrei Saude Challenge"]
readme = "README.md"
packages = [{ include = "config" }, { include = "clinic" }]

[tool.poetry.dependencies]
python = "^3.12"
django = "^5.0.0"
djangorestframework = "^3.15.0"
django-filter = "^24.0"
django-cors-headers = "^4.0.0"
drf-spectacular = "^0.27.0"
psycopg = { version = "^3.1.0", extras = ["binary"] }
dj-database-url = "^2.2.0"
python-decouple = "^3.8"
bleach = "^6.1.0"
requests = "^2.32.0"
gunicorn = "^22.0.0"
whitenoise = "^6.7.0"

[tool.poetry.group.dev.dependencies]
black = "^24.0.0"
ruff = "^0.5.0"
coverage = "^7.5.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.black]
line-length = 88
target-version = ["py312"]

[tool.ruff]
line-length = 88
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]

[tool.coverage.run]
source = ["clinic", "config"]
omit = ["*/migrations/*", "manage.py"]
```

- [ ] **Step 2: Add local environment and ignore files**

Add `.gitignore`:

```gitignore
.env
.venv/
__pycache__/
*.py[cod]
.coverage
htmlcov/
.pytest_cache/
db.sqlite3
staticfiles/
.DS_Store
.terraform/
*.tfstate
*.tfstate.*
terraform.tfvars
```

Add `.env.example`:

```dotenv
DJANGO_ENV=local
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
DATABASE_URL=postgresql://lacrei:lacrei@db:5432/lacrei
API_KEY=local-api-key
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
CSRF_TRUSTED_ORIGINS=http://localhost:8000
ASAAS_BASE_URL=https://sandbox.asaas.com/api
ASAAS_API_KEY=change-me
ASAAS_DEFAULT_BILLING_TYPE=BOLETO
```

- [ ] **Step 3: Add Django entrypoint files**

Add `manage.py`:

```python
#!/usr/bin/env python
import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
```

Add `config/__init__.py`:

```python
```

Add `config/asgi.py`:

```python
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_asgi_application()
```

Add `config/wsgi.py`:

```python
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()
```

Add `clinic/__init__.py`:

```python
```

Add `clinic/apps.py`:

```python
from django.apps import AppConfig


class ClinicConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "clinic"
```

- [ ] **Step 4: Install dependencies and create lockfile**

Run:

```bash
poetry lock
poetry install
```

Expected: dependencies resolve and `poetry.lock` is created.

- [ ] **Step 5: Run lint bootstrap**

Run:

```bash
poetry run black --check .
poetry run ruff check .
```

Expected: both commands pass after formatting any generated files if needed.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml poetry.lock .gitignore .env.example manage.py config clinic
git commit -m "chore: scaffold django project"
```

### Task 2: Settings, URLs, And Healthcheck

**Files:**
- Create: `config/settings.py`
- Create: `config/urls.py`
- Create: `clinic/views.py`
- Create: `clinic/urls.py`

- [ ] **Step 1: Add settings**

Add `config/settings.py`:

```python
from __future__ import annotations

import os
from pathlib import Path

import dj_database_url
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

DJANGO_ENV = config("DJANGO_ENV", default="local")
SECRET_KEY = config("DJANGO_SECRET_KEY", default="unsafe-local-secret")
DEBUG = config("DJANGO_DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config(
    "DJANGO_ALLOWED_HOSTS",
    default="localhost,127.0.0.1",
    cast=lambda value: [host.strip() for host in value.split(",") if host.strip()],
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "rest_framework",
    "clinic",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

API_KEY = config("API_KEY", default="")
ASAAS_BASE_URL = config("ASAAS_BASE_URL", default="https://sandbox.asaas.com/api")
ASAAS_API_KEY = config("ASAAS_API_KEY", default="")
ASAAS_DEFAULT_BILLING_TYPE = config("ASAAS_DEFAULT_BILLING_TYPE", default="BOLETO")

CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000,http://127.0.0.1:3000",
    cast=lambda value: [origin.strip() for origin in value.split(",") if origin.strip()],
)
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="http://localhost:8000",
    cast=lambda value: [origin.strip() for origin in value.split(",") if origin.strip()],
)

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["clinic.permissions.HasAPIKey"],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "rest_framework.views.exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Lacrei Saude Medical Appointments API",
    "DESCRIPTION": "API for professionals, appointments, and Asaas split payments.",
    "VERSION": "1.0.0",
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = DJANGO_ENV in {"staging", "production"}
CSRF_COOKIE_SECURE = DJANGO_ENV in {"staging", "production"}
SECURE_SSL_REDIRECT = DJANGO_ENV in {"staging", "production"} and not DEBUG

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "jsonish": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "jsonish",
        }
    },
    "root": {"handlers": ["console"], "level": os.getenv("LOG_LEVEL", "INFO")},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "clinic": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
```

- [ ] **Step 2: Add temporary API key permission**

Create `clinic/permissions.py`:

```python
from django.conf import settings
from rest_framework.permissions import BasePermission


class HasAPIKey(BasePermission):
    message = "Invalid or missing API key."

    def has_permission(self, request, view) -> bool:
        if getattr(view, "allow_unauthenticated", False):
            return True
        expected_key = settings.API_KEY
        provided_key = request.headers.get("X-API-Key")
        return bool(expected_key and provided_key == expected_key)
```

- [ ] **Step 3: Add healthcheck view and URLs**

Add `clinic/views.py`:

```python
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def healthcheck(request):
    return Response({"status": "ok"})
```

Add `clinic/urls.py`:

```python
from django.urls import path

from clinic import views

urlpatterns = [
    path("health/", views.healthcheck, name="healthcheck"),
]
```

Add `config/urls.py`:

```python
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("clinic.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
```

- [ ] **Step 4: Run Django checks**

Run:

```bash
poetry run python manage.py check
```

Expected: `System check identified no issues`.

- [ ] **Step 5: Commit**

```bash
git add config/settings.py config/urls.py clinic/permissions.py clinic/views.py clinic/urls.py
git commit -m "chore: configure django settings and healthcheck"
```

### Task 3: Models, Soft Delete, And Migrations

**Files:**
- Create: `clinic/models.py`
- Create: `clinic/admin.py`
- Create: `clinic/migrations/__init__.py`
- Generate: `clinic/migrations/0001_initial.py`

- [ ] **Step 1: Add models**

Add `clinic/models.py`:

```python
from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class ActiveQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def delete(self):
        return super().update(is_active=False, deleted_at=timezone.now())


class ActiveManager(models.Manager):
    def get_queryset(self):
        return ActiveQuerySet(self.model, using=self._db).active()


class AllObjectsManager(models.Manager):
    def get_queryset(self):
        return ActiveQuerySet(self.model, using=self._db)


class SoftDeleteModel(models.Model):
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = ActiveManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        self.is_active = False
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_active", "deleted_at", "updated_at"])


class Professional(SoftDeleteModel):
    social_name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, unique=True)
    profession = models.CharField(max_length=120)
    address = models.CharField(max_length=255)
    contact = models.CharField(max_length=120)

    class Meta:
        ordering = ["social_name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.social_name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.social_name


class Appointment(SoftDeleteModel):
    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CREATED = "CREATED", "Created"
        PAID = "PAID", "Paid"
        FAILED = "FAILED", "Failed"
        CANCELED = "CANCELED", "Canceled"

    date = models.DateTimeField()
    professional = models.ForeignKey(
        Professional,
        related_name="appointments",
        on_delete=models.PROTECT,
    )
    customer_name = models.CharField(max_length=150)
    customer_document = models.CharField(max_length=40)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    asaas_payment_id = models.CharField(max_length=80, blank=True)
    asaas_customer_id = models.CharField(max_length=80, blank=True)
    asaas_split = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["date", "id"]

    @property
    def external_reference(self) -> str:
        return f"appointment:{self.id}"

    @property
    def price_as_decimal(self) -> Decimal:
        return Decimal(self.price)

    def __str__(self) -> str:
        return f"{self.customer_name} with {self.professional} at {self.date}"
```

- [ ] **Step 2: Add admin registrations**

Add `clinic/admin.py`:

```python
from django.contrib import admin

from clinic.models import Appointment, Professional


@admin.register(Professional)
class ProfessionalAdmin(admin.ModelAdmin):
    list_display = ("id", "social_name", "slug", "profession", "is_active")
    search_fields = ("social_name", "slug", "profession")
    list_filter = ("is_active", "profession")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "date",
        "professional",
        "customer_name",
        "price",
        "payment_status",
        "is_active",
    )
    search_fields = ("customer_name", "customer_document", "asaas_payment_id")
    list_filter = ("payment_status", "is_active")
```

Create `clinic/migrations/__init__.py`:

```python
```

- [ ] **Step 3: Generate migrations**

Run:

```bash
poetry run python manage.py makemigrations clinic
```

Expected: `clinic/migrations/0001_initial.py` is created with `Professional` and `Appointment`.

- [ ] **Step 4: Run model checks and migrations**

Run:

```bash
poetry run python manage.py check
poetry run python manage.py migrate
```

Expected: system check passes and migrations apply successfully.

- [ ] **Step 5: Commit**

```bash
git add clinic/models.py clinic/admin.py clinic/migrations
git commit -m "feat: add clinic domain models"
```

### Task 4: Serializers And Validation

**Files:**
- Create: `clinic/serializers.py`
- Test: `clinic/tests/test_professionals.py`
- Test: `clinic/tests/test_appointments.py`

- [ ] **Step 1: Write failing serializer tests**

Create `clinic/tests/__init__.py`:

```python
```

Create `clinic/tests/test_professionals.py`:

```python
from django.test import TestCase

from clinic.models import Professional
from clinic.serializers import ProfessionalSerializer


class ProfessionalSerializerTests(TestCase):
    def test_generates_slug_when_missing(self):
        serializer = ProfessionalSerializer(
            data={
                "social_name": "Dra Ana Maria",
                "profession": "Cardiologista",
                "address": "Rua A, 123",
                "contact": "ana@example.com",
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        professional = serializer.save()

        self.assertEqual(professional.slug, "dra-ana-maria")

    def test_rejects_duplicate_slug(self):
        Professional.objects.create(
            social_name="Dra Ana Maria",
            slug="dra-ana",
            profession="Cardiologista",
            address="Rua A",
            contact="ana@example.com",
        )
        serializer = ProfessionalSerializer(
            data={
                "social_name": "Outra Ana",
                "slug": "dra-ana",
                "profession": "Dermatologista",
                "address": "Rua B",
                "contact": "outra@example.com",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("slug", serializer.errors)
```

Create `clinic/tests/test_appointments.py`:

```python
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from clinic.models import Professional
from clinic.serializers import AppointmentSerializer


class AppointmentSerializerTests(TestCase):
    def setUp(self):
        self.professional = Professional.objects.create(
            social_name="Dra Lia",
            slug="dra-lia",
            profession="Psicologa",
            address="Rua C",
            contact="lia@example.com",
        )

    def test_accepts_valid_appointment(self):
        serializer = AppointmentSerializer(
            data={
                "date": (timezone.now() + timedelta(days=1)).isoformat(),
                "professional": self.professional.id,
                "customer_name": "Cliente Teste",
                "customer_document": "12345678900",
                "price": "150.00",
                "asaas_split": [
                    {"walletId": "wallet_1", "percentualValue": 20},
                    {"walletId": "wallet_2", "fixedValue": 10},
                ],
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        appointment = serializer.save()

        self.assertEqual(appointment.price, Decimal("150.00"))

    def test_rejects_past_date(self):
        serializer = AppointmentSerializer(
            data={
                "date": (timezone.now() - timedelta(days=1)).isoformat(),
                "professional": self.professional.id,
                "customer_name": "Cliente Teste",
                "customer_document": "12345678900",
                "price": "150.00",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("date", serializer.errors)

    def test_rejects_inactive_professional(self):
        self.professional.delete()
        serializer = AppointmentSerializer(
            data={
                "date": (timezone.now() + timedelta(days=1)).isoformat(),
                "professional": self.professional.id,
                "customer_name": "Cliente Teste",
                "customer_document": "12345678900",
                "price": "150.00",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("professional", serializer.errors)

    def test_rejects_split_with_two_value_modes(self):
        serializer = AppointmentSerializer(
            data={
                "date": (timezone.now() + timedelta(days=1)).isoformat(),
                "professional": self.professional.id,
                "customer_name": "Cliente Teste",
                "customer_document": "12345678900",
                "price": "150.00",
                "asaas_split": [
                    {
                        "walletId": "wallet_1",
                        "percentualValue": 20,
                        "fixedValue": 5,
                    }
                ],
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("asaas_split", serializer.errors)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
poetry run python manage.py test clinic.tests.test_professionals clinic.tests.test_appointments
```

Expected: FAIL because `clinic.serializers` does not exist.

- [ ] **Step 3: Implement serializers**

Add `clinic/serializers.py`:

```python
from __future__ import annotations

from decimal import Decimal

import bleach
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import serializers

from clinic.models import Appointment, Professional


def clean_text(value: str) -> str:
    return bleach.clean(value.strip(), tags=[], attributes={}, strip=True)


class ProfessionalSerializer(serializers.ModelSerializer):
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
        read_only_fields = ["id", "is_active", "created_at", "updated_at", "deleted_at"]
        extra_kwargs = {
            "slug": {"required": False, "allow_blank": True},
            "social_name": {"max_length": 150},
            "profession": {"max_length": 120},
            "address": {"max_length": 255},
            "contact": {"max_length": 120},
        }

    def validate(self, attrs):
        for field in ("social_name", "profession", "address", "contact"):
            if field in attrs:
                attrs[field] = clean_text(attrs[field])

        slug = attrs.get("slug")
        social_name = attrs.get("social_name") or getattr(self.instance, "social_name", "")
        attrs["slug"] = slugify(slug or social_name)
        if not attrs["slug"]:
            raise serializers.ValidationError({"slug": "Slug could not be generated."})
        return attrs


class AppointmentSerializer(serializers.ModelSerializer):
    professional = serializers.PrimaryKeyRelatedField(queryset=Professional.objects.all())

    class Meta:
        model = Appointment
        fields = [
            "id",
            "date",
            "professional",
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
            "payment_status",
            "asaas_payment_id",
            "asaas_customer_id",
            "is_active",
            "created_at",
            "updated_at",
            "deleted_at",
        ]

    def validate_date(self, value):
        if value < timezone.now():
            raise serializers.ValidationError("Appointment date cannot be in the past.")
        return value

    def validate_price(self, value):
        if value <= Decimal("0"):
            raise serializers.ValidationError("Price must be greater than zero.")
        return value

    def validate_professional(self, value):
        if not value.is_active:
            raise serializers.ValidationError("Professional must be active.")
        return value

    def validate_asaas_split(self, value):
        if value in (None, ""):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("Split must be a list.")

        percentual_sum = Decimal("0")
        for item in value:
            if not isinstance(item, dict):
                raise serializers.ValidationError("Each split item must be an object.")
            wallet_id = item.get("walletId")
            has_fixed = "fixedValue" in item
            has_percent = "percentualValue" in item
            if not wallet_id:
                raise serializers.ValidationError("Each split item requires walletId.")
            if has_fixed == has_percent:
                raise serializers.ValidationError(
                    "Each split item must include exactly one of fixedValue or percentualValue."
                )
            if has_fixed and Decimal(str(item["fixedValue"])) <= Decimal("0"):
                raise serializers.ValidationError("fixedValue must be positive.")
            if has_percent:
                percentual = Decimal(str(item["percentualValue"]))
                if percentual <= Decimal("0") or percentual > Decimal("100"):
                    raise serializers.ValidationError(
                        "percentualValue must be greater than 0 and at most 100."
                    )
                percentual_sum += percentual

        if percentual_sum > Decimal("100"):
            raise serializers.ValidationError("Sum of percentualValue cannot exceed 100.")
        return value

    def validate(self, attrs):
        for field in ("customer_name", "customer_document"):
            if field in attrs:
                attrs[field] = clean_text(attrs[field])
        return attrs
```

- [ ] **Step 4: Run serializer tests**

Run:

```bash
poetry run python manage.py test clinic.tests.test_professionals clinic.tests.test_appointments
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add clinic/serializers.py clinic/tests
git commit -m "feat: add clinic serializers and validation"
```

### Task 5: Professional CRUD API

**Files:**
- Modify: `clinic/views.py`
- Modify: `clinic/urls.py`
- Modify: `clinic/tests/test_professionals.py`

- [ ] **Step 1: Add failing API tests**

Append to `clinic/tests/test_professionals.py`:

```python
from rest_framework import status
from rest_framework.test import APITestCase


class ProfessionalAPITests(APITestCase):
    def setUp(self):
        self.client.credentials(HTTP_X_API_KEY="test-key")

    @classmethod
    def setUpTestData(cls):
        from django.test import override_settings

        cls.override = override_settings(API_KEY="test-key")
        cls.override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.override.disable()
        super().tearDownClass()

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

        hidden_response = self.client.get(f"/api/professionals/{professional_id}/")
        self.assertEqual(hidden_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_filter_by_slug(self):
        Professional.objects.create(
            social_name="Dra Beta",
            slug="dra-beta",
            profession="Psiquiatra",
            address="Rua Dois",
            contact="beta@example.com",
        )

        response = self.client.get("/api/professionals/?slug=dra-beta")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["slug"], "dra-beta")
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
poetry run python manage.py test clinic.tests.test_professionals
```

Expected: FAIL because professional routes/viewsets are not implemented.

- [ ] **Step 3: Implement professional viewset and router**

Replace `clinic/views.py` with:

```python
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from clinic.models import Professional
from clinic.serializers import ProfessionalSerializer


@api_view(["GET"])
@permission_classes([AllowAny])
def healthcheck(request):
    return Response({"status": "ok"})


class ProfessionalViewSet(viewsets.ModelViewSet):
    serializer_class = ProfessionalSerializer
    filterset_fields = ["slug", "profession"]

    def get_queryset(self):
        return Professional.objects.all()
```

Replace `clinic/urls.py` with:

```python
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from clinic import views

router = DefaultRouter()
router.register("professionals", views.ProfessionalViewSet, basename="professional")

urlpatterns = [
    path("health/", views.healthcheck, name="healthcheck"),
    path("api/", include(router.urls)),
]
```

- [ ] **Step 4: Run professional API tests**

Run:

```bash
poetry run python manage.py test clinic.tests.test_professionals
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add clinic/views.py clinic/urls.py clinic/tests/test_professionals.py
git commit -m "feat: add professional crud api"
```

### Task 6: Appointment CRUD API And Professional Search

**Files:**
- Modify: `clinic/views.py`
- Modify: `clinic/urls.py`
- Modify: `clinic/tests/test_appointments.py`

- [ ] **Step 1: Add failing appointment API tests**

Append to `clinic/tests/test_appointments.py`:

```python
from rest_framework import status
from rest_framework.test import APITestCase


class AppointmentAPITests(APITestCase):
    def setUp(self):
        self.client.credentials(HTTP_X_API_KEY="test-key")
        self.professional = Professional.objects.create(
            social_name="Dra Vera",
            slug="dra-vera",
            profession="Nutricionista",
            address="Rua Tres",
            contact="vera@example.com",
        )

    @classmethod
    def setUpTestData(cls):
        from django.test import override_settings

        cls.override = override_settings(API_KEY="test-key")
        cls.override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.override.disable()
        super().tearDownClass()

    def payload(self):
        return {
            "date": (timezone.now() + timedelta(days=2)).isoformat(),
            "professional": self.professional.id,
            "customer_name": "Maria Cliente",
            "customer_document": "12345678900",
            "price": "200.00",
            "asaas_split": [{"walletId": "wallet_1", "percentualValue": 15}],
        }

    def test_create_list_retrieve_update_and_soft_delete_appointment(self):
        create_response = self.client.post(
            "/api/appointments/",
            self.payload(),
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        appointment_id = create_response.data["id"]

        list_response = self.client.get("/api/appointments/")
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data["count"], 1)

        detail_response = self.client.get(f"/api/appointments/{appointment_id}/")
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["customer_name"], "Maria Cliente")

        update_response = self.client.patch(
            f"/api/appointments/{appointment_id}/",
            {"customer_name": "Maria Atualizada"},
            format="json",
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data["customer_name"], "Maria Atualizada")

        delete_response = self.client.delete(f"/api/appointments/{appointment_id}/")
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

        hidden_response = self.client.get(f"/api/appointments/{appointment_id}/")
        self.assertEqual(hidden_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_search_appointments_by_professional_id(self):
        create_response = self.client.post(
            "/api/appointments/",
            self.payload(),
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        response = self.client.get(
            f"/api/professionals/{self.professional.id}/appointments/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["professional"], self.professional.id)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
poetry run python manage.py test clinic.tests.test_appointments
```

Expected: FAIL because appointment routes/viewsets are not implemented.

- [ ] **Step 3: Implement appointment endpoints**

Update `clinic/views.py`:

```python
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from clinic.models import Appointment, Professional
from clinic.serializers import AppointmentSerializer, ProfessionalSerializer


@api_view(["GET"])
@permission_classes([AllowAny])
def healthcheck(request):
    return Response({"status": "ok"})


class ProfessionalViewSet(viewsets.ModelViewSet):
    serializer_class = ProfessionalSerializer
    filterset_fields = ["slug", "profession"]

    def get_queryset(self):
        return Professional.objects.all()

    @action(detail=True, methods=["get"], url_path="appointments")
    def appointments(self, request, pk=None):
        professional = self.get_object()
        queryset = Appointment.objects.filter(professional=professional)
        page = self.paginate_queryset(queryset)
        serializer = AppointmentSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    filterset_fields = ["professional", "payment_status"]

    def get_queryset(self):
        return Appointment.objects.select_related("professional").all()
```

Update `clinic/urls.py`:

```python
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
```

- [ ] **Step 4: Run appointment API tests**

Run:

```bash
poetry run python manage.py test clinic.tests.test_appointments
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add clinic/views.py clinic/urls.py clinic/tests/test_appointments.py
git commit -m "feat: add appointment crud api"
```

### Task 7: API Key Error Tests

**Files:**
- Create: `clinic/tests/test_auth_and_errors.py`
- Modify: `clinic/permissions.py`

- [ ] **Step 1: Add failing auth/error tests**

Create `clinic/tests/test_auth_and_errors.py`:

```python
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase


@override_settings(API_KEY="test-key")
class AuthAndErrorTests(APITestCase):
    def test_missing_api_key_returns_401(self):
        response = self.client.get("/api/professionals/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["detail"], "Invalid or missing API key.")

    def test_invalid_api_key_returns_401(self):
        self.client.credentials(HTTP_X_API_KEY="wrong")

        response = self.client.get("/api/professionals/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_professional_payload_returns_400(self):
        self.client.credentials(HTTP_X_API_KEY="test-key")

        response = self.client.post("/api/professionals/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("social_name", response.data)

    def test_healthcheck_is_public(self):
        response = self.client.get("/health/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"status": "ok"})
```

- [ ] **Step 2: Run tests**

Run:

```bash
poetry run python manage.py test clinic.tests.test_auth_and_errors
```

Expected: PASS. If the missing API key returns `403`, continue to Step 3.

- [ ] **Step 3: Convert auth failure to 401 if needed**

If Step 2 fails with `403`, update `clinic/permissions.py`:

```python
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission


class APIKeyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        expected_key = settings.API_KEY
        provided_key = request.headers.get("X-API-Key")
        if not expected_key or provided_key != expected_key:
            raise AuthenticationFailed("Invalid or missing API key.")
        return (None, None)


class HasAPIKey(BasePermission):
    message = "Invalid or missing API key."

    def has_permission(self, request, view) -> bool:
        if getattr(view, "allow_unauthenticated", False):
            return True
        return True
```

Then update `REST_FRAMEWORK` in `config/settings.py`:

```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["clinic.permissions.APIKeyAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["clinic.permissions.HasAPIKey"],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "rest_framework.views.exception_handler",
}
```

Keep `healthcheck` decorated with `AllowAny`.

- [ ] **Step 4: Run auth tests and full API tests**

Run:

```bash
poetry run python manage.py test clinic.tests
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add clinic/permissions.py config/settings.py clinic/tests/test_auth_and_errors.py
git commit -m "test: cover api key authentication and errors"
```

### Task 8: Asaas Payment Module And Endpoints

**Files:**
- Create: `clinic/asaas.py`
- Modify: `clinic/views.py`
- Modify: `clinic/urls.py`
- Create: `clinic/tests/test_payments.py`

- [ ] **Step 1: Add failing payment tests**

Create `clinic/tests/test_payments.py`:

```python
from datetime import timedelta
from unittest.mock import patch

from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from clinic.models import Appointment, Professional


@override_settings(API_KEY="test-key", ASAAS_DEFAULT_BILLING_TYPE="BOLETO")
class PaymentAPITests(APITestCase):
    def setUp(self):
        self.client.credentials(HTTP_X_API_KEY="test-key")
        self.professional = Professional.objects.create(
            social_name="Dra Nina",
            slug="dra-nina",
            profession="Endocrinologista",
            address="Rua Quatro",
            contact="nina@example.com",
        )
        self.appointment = Appointment.objects.create(
            date=timezone.now() + timedelta(days=3),
            professional=self.professional,
            customer_name="Cliente Pagante",
            customer_document="12345678900",
            price="300.00",
            asaas_customer_id="cus_123",
            asaas_split=[{"walletId": "wallet_1", "percentualValue": 25}],
        )

    @patch("clinic.asaas.AsaasClient.create_payment")
    def test_create_payment_sends_expected_payload(self, create_payment):
        create_payment.return_value = {"id": "pay_123", "status": "PENDING"}

        response = self.client.post(f"/api/appointments/{self.appointment.id}/payment/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["asaas_payment_id"], "pay_123")
        self.assertEqual(response.data["payment_status"], "CREATED")
        payload = create_payment.call_args.args[0]
        self.assertEqual(payload["customer"], "cus_123")
        self.assertEqual(payload["value"], 300.0)
        self.assertEqual(payload["externalReference"], f"appointment:{self.appointment.id}")
        self.assertEqual(payload["split"], [{"walletId": "wallet_1", "percentualValue": 25}])

    def test_create_payment_requires_asaas_customer_id(self):
        self.appointment.asaas_customer_id = ""
        self.appointment.save(update_fields=["asaas_customer_id"])

        response = self.client.post(f"/api/appointments/{self.appointment.id}/payment/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("asaas_customer_id", response.data)

    def test_get_payment_status(self):
        self.appointment.asaas_payment_id = "pay_123"
        self.appointment.payment_status = Appointment.PaymentStatus.CREATED
        self.appointment.save(update_fields=["asaas_payment_id", "payment_status"])

        response = self.client.get(f"/api/appointments/{self.appointment.id}/payment/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["asaas_payment_id"], "pay_123")

    def test_webhook_updates_paid_status(self):
        self.appointment.asaas_payment_id = "pay_123"
        self.appointment.payment_status = Appointment.PaymentStatus.CREATED
        self.appointment.save(update_fields=["asaas_payment_id", "payment_status"])

        response = self.client.post(
            "/api/asaas/webhook/",
            {"event": "PAYMENT_RECEIVED", "payment": {"id": "pay_123"}},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.payment_status, Appointment.PaymentStatus.PAID)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
poetry run python manage.py test clinic.tests.test_payments
```

Expected: FAIL because payment module and endpoints are not implemented.

- [ ] **Step 3: Implement Asaas module**

Add `clinic/asaas.py`:

```python
from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings

from clinic.models import Appointment

logger = logging.getLogger(__name__)


class AsaasError(Exception):
    pass


class AsaasClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = (base_url or settings.ASAAS_BASE_URL).rstrip("/")
        self.api_key = api_key or settings.ASAAS_API_KEY

    def create_payment(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = requests.post(
            f"{self.base_url}/v3/lean/payments",
            json=payload,
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "access_token": self.api_key,
            },
            timeout=15,
        )
        if response.status_code >= 400:
            raise AsaasError(response.text)
        return response.json()


def build_payment_payload(appointment: Appointment) -> dict[str, Any]:
    due_date = appointment.date.date().isoformat()
    return {
        "customer": appointment.asaas_customer_id,
        "billingType": settings.ASAAS_DEFAULT_BILLING_TYPE,
        "value": float(appointment.price),
        "dueDate": due_date,
        "externalReference": appointment.external_reference,
        "split": appointment.asaas_split,
    }


def create_payment_for_appointment(
    appointment: Appointment,
    client: AsaasClient | None = None,
) -> Appointment:
    if not appointment.asaas_customer_id:
        raise ValueError("asaas_customer_id is required to create a payment.")

    client = client or AsaasClient()
    payload = build_payment_payload(appointment)
    result = client.create_payment(payload)
    appointment.asaas_payment_id = result.get("id", "")
    appointment.payment_status = Appointment.PaymentStatus.CREATED
    appointment.save(update_fields=["asaas_payment_id", "payment_status", "updated_at"])
    logger.info("asaas_payment_created appointment_id=%s", appointment.id)
    return appointment


def map_asaas_event_to_status(event: str) -> str | None:
    mapping = {
        "PAYMENT_RECEIVED": Appointment.PaymentStatus.PAID,
        "PAYMENT_CONFIRMED": Appointment.PaymentStatus.PAID,
        "PAYMENT_OVERDUE": Appointment.PaymentStatus.FAILED,
        "PAYMENT_DELETED": Appointment.PaymentStatus.CANCELED,
    }
    return mapping.get(event)
```

- [ ] **Step 4: Add payment views and routes**

Update `clinic/views.py`:

```python
import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from clinic.asaas import AsaasError, create_payment_for_appointment, map_asaas_event_to_status
from clinic.models import Appointment, Professional
from clinic.serializers import AppointmentSerializer, ProfessionalSerializer

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([AllowAny])
def healthcheck(request):
    return Response({"status": "ok"})


@api_view(["POST"])
def asaas_webhook(request):
    event = request.data.get("event")
    payment = request.data.get("payment") or {}
    payment_id = payment.get("id")
    status_value = map_asaas_event_to_status(event)
    if not payment_id or not status_value:
        logger.info("asaas_webhook_ignored event=%s payment_id=%s", event, payment_id)
        return Response({"status": "ignored"})

    updated = Appointment.all_objects.filter(asaas_payment_id=payment_id).update(
        payment_status=status_value
    )
    logger.info(
        "asaas_webhook_processed event=%s payment_id=%s updated=%s",
        event,
        payment_id,
        updated,
    )
    return Response({"status": "processed", "updated": updated})


class ProfessionalViewSet(viewsets.ModelViewSet):
    serializer_class = ProfessionalSerializer
    filterset_fields = ["slug", "profession"]

    def get_queryset(self):
        return Professional.objects.all()

    @action(detail=True, methods=["get"], url_path="appointments")
    def appointments(self, request, pk=None):
        professional = self.get_object()
        queryset = Appointment.objects.filter(professional=professional)
        page = self.paginate_queryset(queryset)
        serializer = AppointmentSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    filterset_fields = ["professional", "payment_status"]

    def get_queryset(self):
        return Appointment.objects.select_related("professional").all()

    @action(detail=True, methods=["get", "post"], url_path="payment")
    def payment(self, request, pk=None):
        appointment = self.get_object()
        if request.method == "GET":
            return Response(
                {
                    "payment_status": appointment.payment_status,
                    "asaas_payment_id": appointment.asaas_payment_id,
                    "asaas_customer_id": appointment.asaas_customer_id,
                    "external_reference": appointment.external_reference,
                }
            )

        try:
            appointment = create_payment_for_appointment(appointment)
        except ValueError as exc:
            return Response(
                {"asaas_customer_id": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except AsaasError:
            logger.exception("asaas_payment_failed appointment_id=%s", appointment.id)
            return Response(
                {"detail": "Failed to create payment."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "payment_status": appointment.payment_status,
                "asaas_payment_id": appointment.asaas_payment_id,
                "asaas_customer_id": appointment.asaas_customer_id,
                "external_reference": appointment.external_reference,
            }
        )
```

Update `clinic/urls.py`:

```python
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from clinic import views

router = DefaultRouter()
router.register("professionals", views.ProfessionalViewSet, basename="professional")
router.register("appointments", views.AppointmentViewSet, basename="appointment")

urlpatterns = [
    path("health/", views.healthcheck, name="healthcheck"),
    path("api/asaas/webhook/", views.asaas_webhook, name="asaas-webhook"),
    path("api/", include(router.urls)),
]
```

- [ ] **Step 5: Run payment tests**

Run:

```bash
poetry run python manage.py test clinic.tests.test_payments
```

Expected: PASS.

- [ ] **Step 6: Run all tests**

Run:

```bash
poetry run python manage.py test
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add clinic/asaas.py clinic/views.py clinic/urls.py clinic/tests/test_payments.py
git commit -m "feat: add asaas payment endpoints"
```

### Task 9: Docker And Compose

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.dockerignore`

- [ ] **Step 1: Add Dockerfile**

Add `Dockerfile`:

```dockerfile
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.8.3 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
    && pip install "poetry==$POETRY_VERSION" \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root

COPY . .
RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
```

- [ ] **Step 2: Add Docker Compose**

Add `docker-compose.yml`:

```yaml
services:
  api:
    build: .
    command: >
      sh -c "python manage.py migrate &&
             gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2"
    env_file:
      - .env
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: lacrei
      POSTGRES_USER: lacrei
      POSTGRES_PASSWORD: lacrei
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U lacrei -d lacrei"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

- [ ] **Step 3: Add dockerignore**

Add `.dockerignore`:

```dockerignore
.git
.venv
__pycache__
*.pyc
.env
.coverage
htmlcov
.terraform
*.tfstate
*.tfstate.*
```

- [ ] **Step 4: Build Docker image**

Run:

```bash
docker build -t lacrei-saude-api .
```

Expected: image builds successfully.

- [ ] **Step 5: Commit**

```bash
git add Dockerfile docker-compose.yml .dockerignore
git commit -m "chore: add docker runtime"
```

### Task 10: GitHub Actions CI/CD And Rollback

**Files:**
- Create: `.github/workflows/ci-cd.yml`
- Create: `.github/workflows/rollback.yml`

- [ ] **Step 1: Add CI/CD workflow**

Add `.github/workflows/ci-cd.yml`:

```yaml
name: CI/CD

on:
  push:
    branches: [main]
    tags: ["v*"]
  pull_request:
  workflow_dispatch:

env:
  IMAGE_NAME: lacrei-saude-api
  REGION: ${{ vars.GCP_REGION || 'southamerica-east1' }}

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install Poetry
        run: pipx install poetry
      - name: Install dependencies
        run: poetry install
      - name: Black check
        run: poetry run black --check .
      - name: Ruff check
        run: poetry run ruff check .

  tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: lacrei
          POSTGRES_USER: lacrei
          POSTGRES_PASSWORD: lacrei
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    env:
      DJANGO_ENV: test
      DJANGO_SECRET_KEY: test-secret
      DJANGO_DEBUG: "false"
      DJANGO_ALLOWED_HOSTS: localhost,127.0.0.1
      DATABASE_URL: postgresql://lacrei:lacrei@localhost:5432/lacrei
      API_KEY: test-key
      CORS_ALLOWED_ORIGINS: http://localhost:3000
      CSRF_TRUSTED_ORIGINS: http://localhost:8000
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install Poetry
        run: pipx install poetry
      - name: Install dependencies
        run: poetry install
      - name: Run migrations
        run: poetry run python manage.py migrate
      - name: Run tests
        run: poetry run coverage run manage.py test
      - name: Coverage report
        run: poetry run coverage report

  build:
    runs-on: ubuntu-latest
    needs: [lint, tests]
    steps:
      - uses: actions/checkout@v4
      - name: Build image
        run: docker build -t $IMAGE_NAME:${{ github.sha }} .

  deploy-staging:
    runs-on: ubuntu-latest
    needs: [build]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    environment: staging
    permissions:
      contents: read
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.GCP_WORKLOAD_IDENTITY_PROVIDER }}
          service_account: ${{ secrets.GCP_DEPLOY_SERVICE_ACCOUNT }}
      - uses: google-github-actions/setup-gcloud@v2
      - name: Configure Docker
        run: gcloud auth configure-docker $REGION-docker.pkg.dev --quiet
      - name: Build and push image
        run: |
          IMAGE="$REGION-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/lacrei-saude/$IMAGE_NAME:${{ github.sha }}"
          docker build -t "$IMAGE" .
          docker push "$IMAGE"
          echo "IMAGE=$IMAGE" >> "$GITHUB_ENV"
      - name: Deploy staging
        run: |
          gcloud run deploy lacrei-saude-staging \
            --image "$IMAGE" \
            --region "$REGION" \
            --platform managed \
            --allow-unauthenticated

  deploy-production:
    runs-on: ubuntu-latest
    needs: [build]
    if: github.event_name == 'workflow_dispatch'
    environment: production
    permissions:
      contents: read
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.GCP_WORKLOAD_IDENTITY_PROVIDER }}
          service_account: ${{ secrets.GCP_DEPLOY_SERVICE_ACCOUNT }}
      - uses: google-github-actions/setup-gcloud@v2
      - name: Configure Docker
        run: gcloud auth configure-docker $REGION-docker.pkg.dev --quiet
      - name: Build and push image
        run: |
          IMAGE="$REGION-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/lacrei-saude/$IMAGE_NAME:${{ github.sha }}"
          docker build -t "$IMAGE" .
          docker push "$IMAGE"
          echo "IMAGE=$IMAGE" >> "$GITHUB_ENV"
      - name: Deploy production
        run: |
          gcloud run deploy lacrei-saude-production \
            --image "$IMAGE" \
            --region "$REGION" \
            --platform managed \
            --allow-unauthenticated
```

- [ ] **Step 2: Add rollback workflow**

Add `.github/workflows/rollback.yml`:

```yaml
name: Rollback Cloud Run

on:
  workflow_dispatch:
    inputs:
      environment:
        description: "Environment to rollback"
        required: true
        type: choice
        options:
          - staging
          - production
      revision:
        description: "Cloud Run revision to receive 100% traffic"
        required: true
        type: string

env:
  REGION: ${{ vars.GCP_REGION || 'southamerica-east1' }}

jobs:
  rollback:
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}
    permissions:
      contents: read
      id-token: write
    steps:
      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.GCP_WORKLOAD_IDENTITY_PROVIDER }}
          service_account: ${{ secrets.GCP_DEPLOY_SERVICE_ACCOUNT }}
      - uses: google-github-actions/setup-gcloud@v2
      - name: Send all traffic to selected revision
        run: |
          SERVICE="lacrei-saude-${{ inputs.environment }}"
          gcloud run services update-traffic "$SERVICE" \
            --region "$REGION" \
            --to-revisions "${{ inputs.revision }}=100"
```

- [ ] **Step 3: Validate workflow YAML presence**

Run:

```bash
ls .github/workflows/ci-cd.yml .github/workflows/rollback.yml
```

Expected: both files exist.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci-cd.yml .github/workflows/rollback.yml
git commit -m "ci: add build deploy and rollback workflows"
```

### Task 11: Terraform GCP Infrastructure

**Files:**
- Create: `infra/terraform/main.tf`
- Create: `infra/terraform/variables.tf`
- Create: `infra/terraform/outputs.tf`
- Create: `infra/terraform/staging.tfvars.example`
- Create: `infra/terraform/production.tfvars.example`

- [ ] **Step 1: Add Terraform variables**

Add `infra/terraform/variables.tf`:

```hcl
variable "project_id" {
  type        = string
  description = "GCP project ID."
}

variable "region" {
  type        = string
  description = "GCP region."
  default     = "southamerica-east1"
}

variable "environment" {
  type        = string
  description = "Deployment environment."
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be staging or production."
  }
}

variable "database_tier" {
  type        = string
  description = "Cloud SQL tier."
  default     = "db-f1-micro"
}

variable "database_password" {
  type        = string
  description = "Database user password."
  sensitive   = true
}

variable "image" {
  type        = string
  description = "Container image to deploy."
}
```

- [ ] **Step 2: Add Terraform resources**

Add `infra/terraform/main.tf`:

```hcl
terraform {
  required_version = ">= 1.6.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_artifact_registry_repository" "api" {
  location      = var.region
  repository_id = "lacrei-saude"
  description   = "Docker images for Lacrei Saude API"
  format        = "DOCKER"
}

resource "google_sql_database_instance" "postgres" {
  name             = "lacrei-saude-${var.environment}"
  database_version = "POSTGRES_16"
  region           = var.region

  settings {
    tier = var.database_tier

    backup_configuration {
      enabled = true
    }
  }
}

resource "google_sql_database" "app" {
  name     = "lacrei"
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "app" {
  name     = "lacrei"
  instance = google_sql_database_instance.postgres.name
  password = var.database_password
}

resource "google_service_account" "cloud_run" {
  account_id   = "lacrei-saude-${var.environment}"
  display_name = "Lacrei Saude ${var.environment} Cloud Run"
}

resource "google_cloud_run_v2_service" "api" {
  name     = "lacrei-saude-${var.environment}"
  location = var.region

  template {
    service_account = google_service_account.cloud_run.email

    containers {
      image = var.image

      ports {
        container_port = 8000
      }

      env {
        name  = "DJANGO_ENV"
        value = var.environment
      }
    }
  }
}
```

- [ ] **Step 3: Add outputs and tfvars examples**

Add `infra/terraform/outputs.tf`:

```hcl
output "artifact_registry_repository" {
  value = google_artifact_registry_repository.api.name
}

output "cloud_run_service" {
  value = google_cloud_run_v2_service.api.name
}

output "cloud_run_uri" {
  value = google_cloud_run_v2_service.api.uri
}

output "cloud_sql_instance" {
  value = google_sql_database_instance.postgres.connection_name
}
```

Add `infra/terraform/staging.tfvars.example`:

```hcl
project_id        = "your-gcp-project"
region            = "southamerica-east1"
environment       = "staging"
database_tier     = "db-f1-micro"
database_password = "replace-with-secret"
image             = "southamerica-east1-docker.pkg.dev/your-gcp-project/lacrei-saude/lacrei-saude-api:staging"
```

Add `infra/terraform/production.tfvars.example`:

```hcl
project_id        = "your-gcp-project"
region            = "southamerica-east1"
environment       = "production"
database_tier     = "db-custom-1-3840"
database_password = "replace-with-secret"
image             = "southamerica-east1-docker.pkg.dev/your-gcp-project/lacrei-saude/lacrei-saude-api:production"
```

- [ ] **Step 4: Validate Terraform formatting**

Run:

```bash
terraform fmt -check infra/terraform
```

Expected: PASS. If Terraform is not installed locally, note this in the final verification.

- [ ] **Step 5: Commit**

```bash
git add infra/terraform
git commit -m "infra: add terraform cloud run foundation"
```

### Task 12: Documentation

**Files:**
- Create: `README.md`
- Create: `docs/decisions-and-improvements.md`

- [ ] **Step 1: Add README**

Add `README.md` with these sections:

```markdown
# Lacrei Saude API

RESTful API for healthcare professionals, appointments, and appointment-linked Asaas split payments.

## Stack

- Python 3.12
- Django
- Django REST Framework
- PostgreSQL
- Poetry
- Docker
- GitHub Actions
- Terraform
- GCP Cloud Run

## Local Setup With Poetry

```bash
cp .env.example .env
poetry install
poetry run python manage.py migrate
poetry run python manage.py runserver
```

## Local Setup With Docker

```bash
cp .env.example .env
docker compose up --build
```

The API runs at `http://localhost:8000`.

## Authentication

Business endpoints require:

```http
X-API-Key: local-api-key
```

## API Docs

- Swagger: `GET /api/docs/`
- OpenAPI schema: `GET /api/schema/`

## Main Endpoints

- `GET /api/professionals/`
- `POST /api/professionals/`
- `GET /api/professionals/{id}/`
- `PATCH /api/professionals/{id}/`
- `DELETE /api/professionals/{id}/`
- `GET /api/appointments/`
- `POST /api/appointments/`
- `GET /api/appointments/{id}/`
- `PATCH /api/appointments/{id}/`
- `DELETE /api/appointments/{id}/`
- `GET /api/professionals/{id}/appointments/`
- `POST /api/appointments/{id}/payment/`
- `GET /api/appointments/{id}/payment/`
- `POST /api/asaas/webhook/`

## Running Tests

```bash
poetry run python manage.py test
```

With coverage:

```bash
poetry run coverage run manage.py test
poetry run coverage report
```

## CI/CD

The GitHub Actions pipeline runs lint, tests, Docker build, staging deploy, and manual production deploy.

Required GitHub secrets:

- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `GCP_DEPLOY_SERVICE_ACCOUNT`
- `GCP_PROJECT_ID`

Required GitHub variables:

- `GCP_REGION`

## Deploy With Terraform

```bash
cd infra/terraform
terraform init
terraform plan -var-file=staging.tfvars
terraform apply -var-file=staging.tfvars
```

Use `production.tfvars` for production.

## Rollback

Rollback is handled by the `Rollback Cloud Run` GitHub Actions workflow.

1. Open the workflow manually.
2. Choose `staging` or `production`.
3. Provide the previous Cloud Run revision name.
4. The workflow sends 100% traffic to that revision with `gcloud run services update-traffic`.

## Asaas Split Payments

Appointments store `price`, `asaas_customer_id`, and `asaas_split`. Payment creation sends a lean payment payload with `customer`, `billingType`, `value`, `dueDate`, `externalReference`, and `split`.

Each split item requires `walletId` and exactly one of `fixedValue` or `percentualValue`.

## Technical Decisions

- API Key authentication keeps the challenge focused while protecting endpoints.
- Soft delete preserves appointment and payment history.
- Django ORM avoids raw SQL and protects against SQL injection in these flows.
- `drf-spectacular` exposes OpenAPI documentation.
- Terraform documents the intended GCP infrastructure for staging and production.
```

- [ ] **Step 2: Add decisions and improvements document**

Add `docs/decisions-and-improvements.md`:

```markdown
# Decisions And Improvements

## Decisions

- Used a lean Django monolith with one `clinic` app to keep the challenge easy to evaluate.
- Used API Key authentication through `X-API-Key`.
- Used soft delete for professionals and appointments to preserve history.
- Used Django ORM and serializers for validation and SQL injection protection.
- Kept Asaas payment code as an internal module instead of a separate app.
- Used Terraform to describe staging and production infrastructure.

## Errors Or Risks Found

- Live deploy cannot be executed without GCP credentials and project-specific secrets.
- Asaas integration is test-safe and mocked in automated tests.
- Cloud SQL private networking and Secret Manager injection may require project-specific adjustments.

## Proposed Improvements

- Add JWT or OAuth2 if end-user authentication becomes required.
- Add webhook signature verification if Asaas provides a configured signing secret.
- Add audit tables for payment status transitions.
- Add rate limiting for public-facing endpoints.
- Add API versioning under `/api/v1/`.
- Add structured JSON logging with trace IDs.
```

- [ ] **Step 3: Check Markdown files exist**

Run:

```bash
ls README.md docs/decisions-and-improvements.md
```

Expected: both files exist.

- [ ] **Step 4: Commit**

```bash
git add README.md docs/decisions-and-improvements.md
git commit -m "docs: add setup deploy and decisions guide"
```

### Task 13: Final Verification

**Files:**
- Modify only files needed to fix verification failures.

- [ ] **Step 1: Run formatting**

Run:

```bash
poetry run black .
poetry run ruff check . --fix
```

Expected: formatting completes.

- [ ] **Step 2: Run lint checks**

Run:

```bash
poetry run black --check .
poetry run ruff check .
```

Expected: PASS.

- [ ] **Step 3: Run Django checks**

Run:

```bash
poetry run python manage.py check
```

Expected: `System check identified no issues`.

- [ ] **Step 4: Run tests**

Run:

```bash
poetry run python manage.py test
```

Expected: all tests pass.

- [ ] **Step 5: Build Docker image**

Run:

```bash
docker build -t lacrei-saude-api .
```

Expected: image builds successfully.

- [ ] **Step 6: Validate Terraform formatting if available**

Run:

```bash
terraform fmt -check infra/terraform
```

Expected: PASS, or record that Terraform is unavailable locally.

- [ ] **Step 7: Review git diff**

Run:

```bash
git status --short
git diff --stat HEAD
```

Expected: only intended files changed.

- [ ] **Step 8: Commit verification fixes**

If formatting or verification changed files:

```bash
git add .
git commit -m "chore: finalize api implementation"
```

If no files changed, do not create an empty commit.

## Self-Review Checklist

- Spec coverage: professionals CRUD, appointments CRUD, search by professional ID, JSON responses, validation, sanitization, API key auth, CORS, SQL injection protection via ORM, logs, APITestCase tests, Poetry, PostgreSQL, Docker, GitHub Actions, Terraform, GCP staging/production, Asaas split, README, rollback, and decisions document are covered.
- Placeholder scan: no unresolved markers or undefined task references should remain in this plan.
- Type consistency: `Professional`, `Appointment`, `asaas_split`, `external_reference`, `payment_status`, `X-API-Key`, and route names are consistent across tasks.
