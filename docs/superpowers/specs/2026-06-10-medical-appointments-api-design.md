# Medical Appointments API Design

## Context

This repository currently contains only the initial Git metadata and `.gitattributes`.
The project will be built from scratch as a RESTful API for managing healthcare
professionals, medical appointments, and appointment-linked payment creation with
Asaas split support.

The implementation should favor a lean monolithic Django structure that is easy
to evaluate, while still including production-oriented pieces such as Docker,
PostgreSQL, API key authentication, OpenAPI docs, Terraform for GCP, GitHub
Actions CI/CD, logging, and rollback documentation.

## Goals

- Build a JSON-only REST API using Python, Django, and Django REST Framework.
- Manage healthcare professionals with full CRUD and soft delete.
- Manage medical appointments with full CRUD, soft delete, professional linkage,
  customer data, price, payment status, and Asaas payment metadata.
- Support searching appointments by professional ID.
- Support unique professional slugs for lookup/filtering.
- Add API key authentication using the `X-API-Key` header.
- Add validation, sanitization, CORS configuration, SQL injection protection via
  ORM usage, access logs, and error logs.
- Add automated tests using `APITestCase`.
- Provide Docker and Poetry setup.
- Provide GitHub Actions workflows with lint, tests, build, deploy, and rollback.
- Provide Terraform definitions for GCP staging and production infrastructure.
- Document setup, tests, deploy, rollback, technical decisions, encountered
  issues, and proposed improvements.

## Non-Goals

- Implementing user registration, login, or JWT authentication.
- Calling the real Asaas API during tests.
- Building separate microservices.
- Building a separate Django app only for payments.
- Performing a live deployment from this development environment.

## Architecture

The project will use a lean monolithic Django structure:

- `config/`: Django settings, URLs, ASGI, and WSGI.
- `clinic/`: the main app containing models, serializers, views, permissions,
  filters, Asaas client/service module, webhook handling, and tests.
- `infra/terraform/`: GCP infrastructure definitions.
- `.github/workflows/`: CI/CD and rollback workflows.
- Root project files: `pyproject.toml`, `poetry.lock`, `Dockerfile`,
  `docker-compose.yml`, `.env.example`, and `README.md`.

This keeps the codebase small and readable for the challenge while still giving
the payment flow a clean internal boundary through service/client modules inside
the same app.

## API Surface

All business endpoints return JSON and require `X-API-Key`.

- `GET /api/professionals/`
- `POST /api/professionals/`
- `GET /api/professionals/{id}/`
- `PUT/PATCH /api/professionals/{id}/`
- `DELETE /api/professionals/{id}/`
- `GET /api/appointments/`
- `POST /api/appointments/`
- `GET /api/appointments/{id}/`
- `PUT/PATCH /api/appointments/{id}/`
- `DELETE /api/appointments/{id}/`
- `GET /api/professionals/{id}/appointments/`
- `POST /api/appointments/{id}/payment/`
- `GET /api/appointments/{id}/payment/`
- `POST /api/asaas/webhook/`
- `GET /api/schema/`
- `GET /api/docs/`
- `GET /health/`

Professional slug lookup will be supported at least through filtering:

- `GET /api/professionals/?slug={slug}`

If implementation remains simple, a detail route by slug may also be added.

## Data Model

### Professional

- `id`
- `social_name`
- `slug`
- `profession`
- `address`
- `contact`
- `is_active`
- `created_at`
- `updated_at`
- `deleted_at`

Rules:

- `id` will use Django's default integer primary key to keep the challenge simple.
- `slug` is unique.
- If `slug` is not provided, it is generated from `social_name`.
- List endpoints return only active records by default.
- Delete performs soft delete by setting `is_active=false` and `deleted_at`.

### Appointment

- `id`
- `date`
- `professional`
- `customer_name`
- `customer_document`
- `price`
- `payment_status`
- `asaas_payment_id`
- `asaas_customer_id`
- `asaas_split`
- `is_active`
- `created_at`
- `updated_at`
- `deleted_at`

Rules:

- `id` will use Django's default integer primary key to keep the challenge simple.
- `professional` is a foreign key to `Professional`.
- New or updated appointments must reference an active professional.
- `customer_name` and `customer_document` are required.
- `price` is required and must be greater than zero.
- `asaas_external_reference` will not be stored separately. It will be derived
  from the appointment ID when creating a payment as `appointment:{id}` for
  easier debugging.
- Delete performs soft delete by setting `is_active=false` and `deleted_at`.

### Payment Status

Expected values:

- `PENDING`
- `CREATED`
- `PAID`
- `FAILED`
- `CANCELED`

## Asaas Payment Flow

Payment support will live as modules inside `clinic`, not as a separate Django
app. The flow will be realistic but test-safe:

1. A client creates an appointment with customer data, price, and optional split.
2. A client calls `POST /api/appointments/{id}/payment/`.
3. The service builds an Asaas payment payload from the appointment.
4. The Asaas client sends the request outside tests; tests mock this client.
5. The appointment stores returned payment metadata and updates `payment_status`.
6. The webhook endpoint receives events and updates the appointment status when
   the event can be matched by payment ID or external reference.

The Asaas payload design is based on the lean payment creation endpoint and split
documentation:

- `customer`
- `billingType`
- `value`
- `dueDate`
- `externalReference`
- `split`

`asaas_split` will be a list of objects. Each item must include `walletId` and
exactly one of:

- `fixedValue`
- `percentualValue`

Validation rules:

- `fixedValue` must be positive.
- `percentualValue` must be greater than 0 and at most 100.
- The sum of all percentage values must not exceed 100.
- The remaining value stays with the issuing account, following Asaas split
  behavior.

## Validation And Sanitization

- DRF serializers will centralize input validation.
- Required fields will be explicit.
- Strings will be trimmed.
- Free text fields such as address and contact will be sanitized with `bleach`.
- Max lengths will be defined for all string fields.
- `date` must be valid and cannot be in the past.
- Pagination will be enabled with conservative defaults.
- Filtering will use `django-filter` or explicit queryset filtering.
- SQL injection protection will rely on the Django ORM and no raw SQL for these
  flows.

## Authentication, CORS, And Security

- Business endpoints require `X-API-Key`.
- The expected key is loaded from environment variables.
- Missing or invalid API keys return `401`.
- CORS origins are environment-specific through `CORS_ALLOWED_ORIGINS`.
- Staging and production must not use wildcard CORS.
- `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, and Django `SECURE_*` settings will be
  environment-aware.
- Secrets will not be committed. `.env.example` documents required variables.
- Swagger/OpenAPI will be public locally and require `X-API-Key` in staging and
  production.

## Error Handling

Expected API error behavior:

- Validation error: `400` with field-level JSON errors.
- Invalid or missing API key: `401`.
- Missing or soft-deleted resource: `404`.
- Inactive professional used in an appointment: `400`.
- Unexpected errors: JSON error response plus server-side error logs.

## Logging

- Access logs include method, path, status code, and duration.
- Error logs include traceback and request context safe for logs.
- Cloud Run collects stdout/stderr into Cloud Logging.
- Webhook processing logs received event type, matched appointment/payment, and
  outcome without logging sensitive customer documents in full.

## Testing

Tests will use Django `APITestCase`.

Required coverage:

- Professional CRUD.
- Professional slug uniqueness and slug filtering.
- Professional validation errors and soft delete behavior.
- Appointment CRUD.
- Appointment validation errors for missing fields and invalid professional.
- Appointment creation/update with customer name and document.
- Appointment soft delete behavior.
- Search appointments by professional ID.
- API key missing and invalid cases.
- Asaas split validation.
- Payment creation with mocked Asaas client and payload assertions.
- Webhook stub behavior for relevant payment status updates.

## Docker And Local Development

Poetry manages Python dependencies.

Docker setup:

- `Dockerfile` builds the Django application and runs Gunicorn.
- `docker-compose.yml` runs API and PostgreSQL.
- `.env.example` documents variables such as database URL, API key, CORS origins,
  Asaas credentials, Django secret key, and environment name.

The README will include local setup with Poetry, Docker setup, migrations, test
commands, and common troubleshooting.

## CI/CD

GitHub Actions workflows include:

- `lint`: install dependencies with Poetry and run format/lint checks.
- `tests`: run PostgreSQL service container, migrations, and Django tests.
- `build`: build Docker image.
- `deploy-staging`: push image to Artifact Registry and deploy to Cloud Run
  staging.
- `deploy-production`: deploy to Cloud Run production through a manual GitHub
  Actions trigger.
- `rollback`: manually triggered workflow that redirects Cloud Run traffic to a
  previous revision or redeploys a selected previous image.

## GCP Infrastructure With Terraform

Terraform files under `infra/terraform/` will declare or prepare:

- Artifact Registry repository.
- Cloud Run service for staging.
- Cloud Run service for production.
- Cloud SQL PostgreSQL instance/database/user.
- Service accounts.
- IAM permissions with least practical privilege.
- Secret Manager references for app secrets.
- Environment-specific variables for staging and production.

The README will document `terraform init`, `terraform plan`, and `terraform apply`
for each environment.

## Documentation

The README will cover:

- Project overview.
- Local setup with Poetry.
- Docker setup.
- Environment variables.
- Running migrations.
- Running tests.
- API authentication.
- Main endpoints and example payloads.
- OpenAPI/Swagger usage.
- CI/CD flow.
- Terraform/GCP deploy flow.
- Rollback flow using GitHub Actions and Cloud Run revisions.
- Technical decisions.
- Asaas split integration notes.
- Errors encountered, decisions made, and proposed improvements.

## Open Questions Resolved

- Authentication: API key through `X-API-Key`.
- Payments: same Django service, no separate app.
- Payment relation: appointments include customer data, price, status, payment ID,
  customer ID, and split list.
- Asaas external reference: derived from appointment ID.
- Delete behavior: soft delete.
- API docs: OpenAPI/Swagger through `drf-spectacular`.
- Infrastructure: Terraform included for GCP staging and production.
- Project shape: lean monolithic Django app.
