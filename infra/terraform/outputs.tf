output "artifact_registry_repository" {
  description = "Artifact Registry repository ID."
  value       = google_artifact_registry_repository.api.id
}

output "cloud_run_service" {
  description = "Cloud Run service name."
  value       = google_cloud_run_v2_service.api.name
}

output "cloud_run_uri" {
  description = "Cloud Run service URI."
  value       = google_cloud_run_v2_service.api.uri
}

output "cloud_sql_instance" {
  description = "Cloud SQL instance connection name."
  value       = google_sql_database_instance.postgres.connection_name
}
