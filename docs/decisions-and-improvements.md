# Decisions and Improvements

This document records the main implementation choices, risks found during delivery, and improvements that should be considered as the API moves from challenge scope toward production operation.

## Decisions

- Lean monolith: Django, DRF, serializers, migrations, payment integration, and deployment configuration live in one repository. This keeps operational complexity low while the healthcare professional, appointment, and payment domains are still compact.
- API key authentication: authenticated endpoints require an `X-API-Key` header. This is simple for server-to-server or controlled partner access and keeps the first version easy to operate.
- Soft delete: professionals and appointments use `is_active`, `deleted_at`, and managers that hide inactive rows by default. This preserves records that may matter for payment, scheduling, support, or audit review.
- ORM and serializers: Django ORM models own persistence rules, while DRF serializers own request validation, text cleanup, and Asaas split validation.
- Asaas internal module: payment behavior is isolated in `clinic/asaas.py`, keeping request construction, external calls, response handling, and status mapping out of API views.
- Terraform: GCP resources are described as infrastructure as code, including Artifact Registry, Cloud SQL, Cloud Run, IAM, and Secret Manager access.
- GitHub Actions deployment: CI checks run before build and deploy jobs; staging deploys on pushes to `main`, while production deploy is manual from `main`.

## Errors and Risks Found

- Live deploy requires credentials and secrets: GitHub needs `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_DEPLOY_SERVICE_ACCOUNT`, and `GCP_PROJECT_ID`; `GCP_REGION` is optional and defaults to `southamerica-east1`. GCP must have the expected IAM, Artifact Registry, Cloud Run, Cloud SQL, and Secret Manager setup.
- Docker daemon may be unavailable locally: `docker compose up --build` depends on a running Docker daemon, so local validation may need Poetry and SQLite/PostgreSQL instead.
- Terraform CLI may be unavailable locally: infrastructure planning and apply commands require Terraform to be installed and authenticated to the target GCP project.
- Asaas is mocked in tests: this keeps tests deterministic and avoids external calls, but it does not prove sandbox credentials, Asaas payload compatibility, or webhook behavior against the live provider.
- Cloud SQL and Secret Manager settings are project-specific: database sizing, instance connection names, secret names, network posture, IAM bindings, and allowed origins must be reviewed for each GCP project.
- Webhook signature verification is not implemented yet: the webhook currently trusts authenticated API access and event shape; public webhook exposure should verify signatures or another trusted Asaas authenticity signal.
- API key authentication is coarse-grained: one shared key does not provide user identity, scoped permissions, key rotation metadata, or tenant-level isolation.
- Audit history is limited: soft delete preserves rows, but there are no audit tables for who changed a record, what changed, or why.
- Operational visibility is basic: logging exists, but structured request, payment, and webhook logs would make production support easier.

## Proposed Improvements

- Add JWT or OAuth2 for user-aware access, scoped permissions, token expiry, and safer partner integrations.
- Add webhook signature verification and replay protection before exposing Asaas webhooks to the public internet.
- Add audit tables or an event log for professional changes, appointment changes, payment transitions, and webhook processing.
- Add rate limiting for authenticated API routes and stricter limits for webhook/payment endpoints.
- Introduce API versioning, such as `/api/v1/`, before external clients depend on the current URL contract.
- Add structured logging with request IDs, appointment IDs, Asaas payment IDs, webhook event IDs, latency, and error categories.
- Add live Asaas sandbox contract tests that run only with explicit credentials, separate from normal CI.
- Add migration/deploy runbooks for Cloud SQL, including backup restore checks and pre-production migration validation.
- Add secret rotation guidance for `API_KEY`, `DJANGO_SECRET_KEY`, and `ASAAS_API_KEY`.
- Add environment-specific Terraform backend configuration once the target GCP project and state storage conventions are known.
