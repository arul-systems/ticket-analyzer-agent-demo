# Bridges Managed Kafka -> Eventarc. Eventarc has no native Managed Kafka
# trigger source - confirmed via `gcloud eventarc providers list` and
# `gcloud eventarc providers describe managedkafka.googleapis.com` (NOT_FOUND)
# against a live project, after a real `terraform apply` failed trying to use
# "google.cloud.managedkafka.topic.v1.messagePublished" as an event type.
#
# The fix: a Kafka Connect Pub/Sub Sink Connector (provisioned outside
# Terraform - see terraform/setup-kafka-connect.sh; there is no Terraform
# resource for Managed Kafka Connect clusters/connectors yet) mirrors the
# support-tickets topic into this Pub/Sub topic, and Eventarc triggers off
# Pub/Sub instead (a provider confirmed present in the same project).
#
# IAM for this topic (Kafka Connect's publish access, Pub/Sub's ability to
# mint invocation tokens) lives in iam.tf alongside the rest of the project's
# IAM bindings.

resource "google_pubsub_topic" "ticket_events" {
  project = var.gcp_project_id
  name    = "ticket-events"
}
