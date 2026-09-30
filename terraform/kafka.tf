# NOTE: Managed Service for Apache Kafka's Terraform resources are a recent
# addition to the google provider. Field names below were checked against the
# live provider schema (v6.50.0) with `terraform validate`, but re-run that
# yourself before applying in case the schema has moved on since.

resource "google_project_service" "managed_kafka" {
  project = var.gcp_project_id
  service = "managedkafka.googleapis.com"

  disable_on_destroy = false
}

resource "google_managed_kafka_cluster" "ticket_analyzer" {
  project    = var.gcp_project_id
  cluster_id = "ticket-analyzer-kafka"
  location   = var.gcp_region

  # 3 vCPU / 3 GiB is the documented minimum capacity for a Managed Kafka cluster.
  capacity_config {
    vcpu_count   = 3
    memory_bytes = 3221225472 # 3 GiB
  }

  gcp_config {
    access_config {
      network_configs {
        # Uses the auto-created "default" subnet in the target region/project.
        # Point this at your own subnet if you're not using the default VPC.
        subnet = "projects/${var.gcp_project_id}/regions/${var.gcp_region}/subnetworks/default"
      }
    }
  }

  labels = {
    project = "ticket-analyzer-agent-demo"
  }

  depends_on = [google_project_service.managed_kafka]
}

resource "google_managed_kafka_topic" "support_tickets" {
  project  = var.gcp_project_id
  topic_id = "support-tickets"
  cluster  = google_managed_kafka_cluster.ticket_analyzer.cluster_id
  location = var.gcp_region

  partition_count    = 3
  replication_factor = 3
}

output "kafka_cluster_name" {
  description = "Fully qualified resource name of the Managed Kafka cluster."
  value       = google_managed_kafka_cluster.ticket_analyzer.name
}

# The google_managed_kafka_cluster resource does not expose a bootstrap
# address attribute (checked against the live provider schema). Managed
# Service for Apache Kafka's documented bootstrap address format is:
#   bootstrap.<cluster_id>.<region>.managedkafka.<project_id>.cloud.goog:9092
# Verify this against the current "Connect a client" docs before using it -
# confirm it, then set it as KAFKA_BOOTSTRAP_SERVERS for the agent.
output "kafka_bootstrap_address_guess" {
  description = "Best-effort bootstrap address per GCP's documented naming convention - verify before use."
  value       = "bootstrap.ticket-analyzer-kafka.${var.gcp_region}.managedkafka.${var.gcp_project_id}.cloud.goog:9092"
}
