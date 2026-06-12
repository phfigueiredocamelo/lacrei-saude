variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "region" {
  description = "GCP region for regional resources."
  type        = string
  default     = "southamerica-east1"
}

variable "environment" {
  description = "Deployment environment."
  type        = string

  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Environment must be either staging or production."
  }
}

variable "database_tier" {
  description = "Cloud SQL machine tier."
  type        = string
  default     = "db-f1-micro"
}

variable "database_password" {
  description = "Password for the application database user."
  type        = string
  sensitive   = true
}

variable "image" {
  description = "Container image for the API service."
  type        = string
}

variable "django_allowed_hosts" {
  description = "Comma-separated Django allowed hosts."
  type        = string
}

variable "cors_allowed_origins" {
  description = "Comma-separated CORS allowed origins."
  type        = string
}

variable "csrf_trusted_origins" {
  description = "Comma-separated CSRF trusted origins."
  type        = string
}

variable "secret_names" {
  description = "Existing Secret Manager secret names consumed by Cloud Run."
  type = object({
    django_secret_key = string
    api_key           = string
    database_url      = string
    asaas_api_key     = string
  })
}

variable "asaas_base_url" {
  description = "Asaas API base URL for the environment."
  type        = string
}
