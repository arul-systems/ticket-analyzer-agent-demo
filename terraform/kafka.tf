# NOTE: Managed Service for Apache Kafka's Terraform resources are a recent
# addition to the google provider. Field names below were checked against the
# live provider schema (v8.5.0) with `tofu validate`, but re-run that
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

      # The cluster is otherwise only reachable via Private Service Connect
      # from within the connected VPC - this opens it to one external IP
      # (e.g. for running scripts/produce_test_ticket.py from a local
      # machine). Requires google provider >= 8.3.0.
      public_cluster_config {
        allowed_source_ip_ranges = ["${var.kafka_allowed_source_ip}/32"]
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

# google_managed_kafka_cluster.bootstrap_address was added in provider
# 8.3.0 (absent in 6.x, which this project originally pinned to - it
# genuinely wasn't derivable from cluster_id/project/region before). It's
# the hostname only; append :9092 for SASL or :9192 for mTLS.
output "kafka_bootstrap_address" {
  description = "Bootstrap address for KAFKA_BOOTSTRAP_SERVERS (SASL port 9092)."
  value       = "${google_managed_kafka_cluster.ticket_analyzer.bootstrap_address}:9092"
}
