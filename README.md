# Lacrei Saude API

REST API for healthcare professionals, appointment scheduling, and Asaas split payment orchestration. The service is built as a lean Django monolith so the domain model, API validation, payment integration, migrations, tests, and deploy configuration can evolve together while the product surface is still compact.

## Stack

- Python 3.12
- Django 5 and Django REST Framework
- PostgreSQL in Docker, with SQLite as the local fallback when `DATABASE_URL` is not set
- drf-spectacular for OpenAPI and Swagger UI
- django-filter, django-cors-headers, WhiteNoise, Gunicorn
- Poetry for dependency management
- Docker Compose for local container execution
- GitHub Actions for lint, tests, image build, deploy, and rollback workflows
- Terraform for GCP Artifact Registry, Cloud SQL, Cloud Run, Secret Manager access, and IAM wiring

## Local Setup With Poetry

Install Poetry, then create the local environment file and install dependencies:

```bash
cp .env.example .env
poetry install
```

For SQLite fallback with Poetry, remove or comment `DATABASE_URL` in `.env`.
The example `DATABASE_URL` uses the Docker Compose hostname `db`; for a local
PostgreSQL server outside Compose, change the host to `localhost` or another
reachable database host.

Apply migrations and start the development server:

```bash
poetry run python manage.py migrate
poetry run python manage.py runserver
```

The API runs on `http://127.0.0.1:8000/` by default.

## Docker Setup

Docker Compose starts PostgreSQL and the API container. The API service runs migrations before Gunicorn starts.

```bash
cp .env.example .env
docker compose up --build
```

If the local Docker daemon is unavailable, use the Poetry setup with SQLite or point `DATABASE_URL` at an available PostgreSQL instance.

## Environment Variables

Copy `.env.example` to `.env` for local development. The main variables are:

| Variable | Purpose |
| --- | --- |
| `DJANGO_ENV` | Runtime environment: `local`, `test`, `staging`, or `production`. |
| `DJANGO_SECRET_KEY` | Django signing secret. Must be configured outside local. |
| `DJANGO_DEBUG` | Enables debug behavior locally. Must be `false` outside local. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated host allowlist. |
| `DATABASE_URL` | Database connection URL. Docker uses PostgreSQL; local fallback is SQLite. |
| `API_KEY` | Shared API key required in the `X-API-Key` request header. |
| `CORS_ALLOWED_ORIGINS` | Comma-separated browser origins allowed for CORS. |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated trusted origins for CSRF checks. |
| `ASAAS_BASE_URL` | Asaas API base URL, usually sandbox in staging and production API in production. |
| `ASAAS_API_KEY` | Asaas access token used by the payment client. |
| `ASAAS_DEFAULT_BILLING_TYPE` | Billing type sent to Asaas, such as `BOLETO`. |

For staging and production, `DJANGO_SECRET_KEY`, `API_KEY`, `DATABASE_URL`, and `ASAAS_API_KEY` are expected to come from GCP Secret Manager through the Terraform-managed Cloud Run service.

## Migrations

Run migrations before serving the API:

```bash
poetry run python manage.py migrate
```

Docker Compose also runs migrations automatically when the `api` service starts.

## Tests and Coverage

Run the Django test suite:

```bash
poetry run python manage.py test
```

Run tests with coverage:

```bash
poetry run coverage run manage.py test
poetry run coverage report
```

The CI workflow also runs Black, Ruff, migrations, tests, and coverage reporting.

## API Authentication

All API routes use shared API key authentication unless explicitly marked public. Send the configured key in the `X-API-Key` header:

```bash
curl -H "X-API-Key: local-api-key" http://127.0.0.1:8000/api/professionals/
```

`GET /health/` is public. Swagger and schema endpoints are available for API discovery.

## Main Endpoints

- `GET /health/` - health check.
- `/api/professionals/` - list, create, retrieve, update, and soft-delete professionals.
- `GET /api/professionals/{id}/appointments/` - list appointments for a professional.
- `/api/appointments/` - list, create, retrieve, update, and soft-delete appointments.
- `GET /api/appointments/{id}/payment/` - read payment state for an appointment.
- `POST /api/appointments/{id}/payment/` - create an Asaas payment for an appointment.
- `POST /api/asaas/webhook/` - receive Asaas payment events and update appointment payment status. This endpoint currently requires the shared `X-API-Key`.
- `GET /api/schema/` - OpenAPI schema.
- `GET /api/docs/` - Swagger UI.

## OpenAPI and Swagger

The OpenAPI schema is served at `/api/schema/`, and the Swagger UI is served at `/api/docs/`. When testing authenticated endpoints through Swagger or `curl`, include the same `X-API-Key` header used by the API.

## Asaas Split Integration Notes

Payment creation is isolated in `clinic/asaas.py`. `POST /api/appointments/{id}/payment/` builds a payload from the appointment, sends it to Asaas, stores the returned `asaas_payment_id`, and moves the appointment to `CREATED`.

Appointments accept an `asaas_split` JSON list. Each split item must include `walletId` and exactly one of `fixedValue` or `percentualValue`; total percentual split values cannot exceed 100. Tests mock the Asaas client, so local and CI test runs do not call the external API.

The webhook endpoint maps Asaas events such as `PAYMENT_RECEIVED`, `PAYMENT_CONFIRMED`, `PAYMENT_OVERDUE`, and `PAYMENT_DELETED` into local payment states. It currently requires the shared `X-API-Key`; public provider webhooks need compatible header configuration or a dedicated Asaas verification mechanism before production use.

## CI/CD Flow

GitHub Actions workflows live in `.github/workflows/`.

- Pull requests run lint and tests.
- Pushes to `main` run lint, tests, build, and deploy to the `staging` GitHub environment.
- Manual `workflow_dispatch` from `main` can deploy to the `production` GitHub environment.
- Deploy jobs authenticate to GCP with Workload Identity, configure Docker for Artifact Registry, build and push the image, then deploy the image to Cloud Run.
- Apply Terraform before using the deploy workflows. The GitHub Actions deploy jobs are image rollouts; runtime configuration such as Cloud SQL attachment, Secret Manager references, service account, invoker IAM, and environment variables are managed by Terraform.

Required GitHub secrets:

- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `GCP_DEPLOY_SERVICE_ACCOUNT`
- `GCP_PROJECT_ID`

Optional GitHub variable:

- `GCP_REGION`, for example `southamerica-east1`. Defaults to `southamerica-east1` when unset.

## Terraform and GCP Deploy Flow

Terraform configuration is in `infra/terraform`. The examples below use the provided `staging.tfvars.example` and `production.tfvars.example` files as templates. Copy them to environment-specific `.tfvars` files with real values before applying.

Initialize Terraform:

```bash
cd infra/terraform
terraform init
```

Plan staging:

```bash
terraform plan -var-file=staging.tfvars
```

Apply staging:

```bash
terraform apply -var-file=staging.tfvars
```

Plan production:

```bash
terraform plan -var-file=production.tfvars
```

Apply production:

```bash
terraform apply -var-file=production.tfvars
```

Terraform expects project-specific GCP values, existing Secret Manager secret names, and a container image URI. Cloud SQL, Secret Manager, IAM, and Cloud Run settings may need project-specific adjustments before a live deploy. Apply this infrastructure before running the GitHub Actions deploy workflow so Cloud Run already has the expected runtime configuration. If the Terraform CLI is unavailable locally, run these commands in an environment that has Terraform installed and authenticated to the target GCP project.

## Rollback Flow

Rollback is handled by the `Rollback Cloud Run` GitHub Actions workflow.

1. Open the rollback workflow in GitHub Actions.
2. Choose the target environment: `staging` or `production`.
3. Enter the Cloud Run revision name that should receive traffic.
4. Run the workflow. Production rollback is restricted to runs from `main`.
5. The workflow authenticates to GCP, validates that the revision exists for `lacrei-saude-{environment}`, then updates Cloud Run traffic so the selected revision receives 100%.

You can find revision names in the Cloud Run service revision list or through `gcloud run revisions list`.

## Technical Decisions

- Keep the system as a lean monolith while the bounded context is small.
- Use API key authentication through `X-API-Key` for the current partner-style API surface.
- Use soft delete for professionals and appointments to preserve operational history.
- Keep validation in DRF serializers and persistence in Django ORM models.
- Isolate Asaas calls behind a small internal module so tests can mock the integration boundary.
- Provision cloud infrastructure with Terraform and deploy application revisions through GitHub Actions and Cloud Run.

See `docs/decisions-and-improvements.md` for the fuller decision log, known risks, and proposed improvements.
