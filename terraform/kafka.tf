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

  partition_count    = 1
  replication_factor = 1
}

output "kafka_cluster_name" {
  description = "Fully qualified resource name of the Managed Kafka cluster."
  value       = google_managed_kafka_cluster.ticket_analyzer.name
}

# Neither the google_managed_kafka_cluster resource nor any data source
# exposes a bootstrap address attribute (checked against the live provider
# schema - genuinely not there, not just undocumented). The real address is
# per-cluster and includes generated id segments, e.g.:
#   bootstrap-gjomj5xlb-tbpbb71zu3w.aba09531.us-central1.managedkafka.s.cloud.goog:9092
# It is NOT derivable from cluster_id/project/region - fetch it after the
# cluster reaches ACTIVE state with:
#   gcloud managed-kafka clusters describe ticket-analyzer-kafka \
#     --project=<project> --location=<region> --format='value(bootstrapAddress)'
# then set it as KAFKA_BOOTSTRAP_SERVERS for the agent.
