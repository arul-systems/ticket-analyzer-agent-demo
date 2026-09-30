# "Cloud Run functions" are Cloud Functions (2nd gen) under the hood, which
# is why this uses google_cloudfunctions2_function rather than a plain Cloud
# Run service - it's the only Terraform resource that supports deploying
# from source (build_config.source) instead of a pre-built container image.
#
# Service accounts and IAM bindings for this function live in iam.tf.

# Placeholder package used only to create the function; real code is deployed
# by CI (e.g. `gcloud functions deploy` / `gcloud run deploy --source`).
resource "google_storage_bucket" "function_source" {
  project                     = var.gcp_project_id
  name                        = "${var.gcp_project_id}-ticket-analyzer-fn-source"
  location                    = var.gcp_region
  uniform_bucket_level_access = true
}

data "archive_file" "placeholder" {
  type        = "zip"
  source_dir  = "${path.module}/function-placeholder"
  output_path = "${path.module}/function-placeholder.zip"
}

resource "google_storage_bucket_object" "placeholder" {
  name   = "placeholder-${data.archive_file.placeholder.output_md5}.zip"
  bucket = google_storage_bucket.function_source.name
  source = data.archive_file.placeholder.output_path
}

resource "google_cloudfunctions2_function" "ticket_analyzer" {
  project  = var.gcp_project_id
  name     = "ticket-analyzer-agent"
  location = var.gcp_region

  build_config {
    runtime     = "python312"
    entry_point = "handle_ticket_event"

    source {
      storage_source {
        bucket = google_storage_bucket.function_source.name
        object = google_storage_bucket_object.placeholder.name
      }
    }
  }

  service_config {
    service_account_email = google_service_account.function.email
    available_memory      = "512Mi"
    timeout_seconds       = 60
    min_instance_count    = 0
    max_instance_count    = 10

    environment_variables = {
      GCP_PROJECT_ID    = var.gcp_project_id
      GCP_LOCATION      = var.gcp_region
      VERTEX_MODEL_NAME = "claude-sonnet-5-5"
    }
  }

  # Triggers off the Pub/Sub bridge topic (see pubsub.tf), not Kafka directly -
  # Eventarc has no Managed Kafka source. Verified against the live provider:
  # `gcloud eventarc providers describe pubsub.googleapis.com` confirms this
  # event type and that `type` is the only filterable attribute (set
  # implicitly via event_type/pubsub_topic, no event_filters block needed).
  event_trigger {
    trigger_region        = var.gcp_region
    event_type            = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic          = google_pubsub_topic.ticket_events.id
    retry_policy          = "RETRY_POLICY_RETRY"
    service_account_email = google_service_account.trigger.email
  }

  depends_on = [
    google_project_iam_member.trigger_event_receiver,
    google_pubsub_topic_iam_member.connect_publisher,
    google_service_account_iam_member.pubsub_can_mint_trigger_tokens,
  ]

  lifecycle {
    ignore_changes = [build_config[0].source]
  }
}
