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

data "google_secret_manager_secret" "django_secret_key" {
  secret_id = var.secret_names.django_secret_key
}

data "google_secret_manager_secret" "api_key" {
  secret_id = var.secret_names.api_key
}

data "google_secret_manager_secret" "database_url" {
  secret_id = var.secret_names.database_url
}

data "google_secret_manager_secret" "asaas_api_key" {
  secret_id = var.secret_names.asaas_api_key
}

locals {
  runtime_secrets = {
    DJANGO_SECRET_KEY = data.google_secret_manager_secret.django_secret_key.secret_id
    API_KEY           = data.google_secret_manager_secret.api_key.secret_id
    DATABASE_URL      = data.google_secret_manager_secret.database_url.secret_id
    ASAAS_API_KEY     = data.google_secret_manager_secret.asaas_api_key.secret_id
  }
}

resource "google_project_iam_member" "cloud_run_sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}

resource "google_secret_manager_secret_iam_member" "cloud_run_secret_access" {
  for_each = local.runtime_secrets

  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run.email}"
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

      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }

      env {
        name  = "DJANGO_ENV"
        value = var.environment
      }

      env {
        name  = "DJANGO_DEBUG"
        value = "false"
      }

      env {
        name  = "DJANGO_ALLOWED_HOSTS"
        value = var.django_allowed_hosts
      }

      env {
        name  = "CORS_ALLOWED_ORIGINS"
        value = var.cors_allowed_origins
      }

      env {
        name  = "CSRF_TRUSTED_ORIGINS"
        value = var.csrf_trusted_origins
      }

      env {
        name  = "ASAAS_BASE_URL"
        value = var.asaas_base_url
      }

      dynamic "env" {
        for_each = local.runtime_secrets

        content {
          name = env.key

          value_source {
            secret_key_ref {
              secret  = env.value
              version = "latest"
            }
          }
        }
      }
    }

    volumes {
      name = "cloudsql"

      cloud_sql_instance {
        instances = [google_sql_database_instance.postgres.connection_name]
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 5
    }
  }

  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
    ]
  }

  depends_on = [
    google_project_iam_member.cloud_run_sql_client,
    google_secret_manager_secret_iam_member.cloud_run_secret_access,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  name     = google_cloud_run_v2_service.api.name
  location = google_cloud_run_v2_service.api.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}
