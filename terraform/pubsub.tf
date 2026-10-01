# The producer (scripts/produce_test_ticket.py, or any real ticketing system)
# publishes ticket events directly onto this topic. Eventarc triggers the
# Cloud Run function off it (see the event_trigger block in function.tf).
#
# Whoever runs the producer needs roles/pubsub.publisher on this topic or the
# project - not granted here, since that's a human/local ADC identity rather
# than a service account this project owns.

resource "google_pubsub_topic" "support_tickets" {
  project = var.gcp_project_id
  name    = "support-tickets"
}
