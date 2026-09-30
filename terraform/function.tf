# "Cloud Run functions" are Cloud Functions (2nd gen) under the hood, which
# is why this uses google_cloudfunctions2_function rather than a plain Cloud
# Run service - it's the only Terraform resource that supports deploying
# from source (build_config.source) instead of a pre-built container image.

resource "google_service_account" "function" {
  project      = var.gcp_project_id
  account_id   = "ticket-analyzer-fn"
  display_name = "Ticket Analyzer Cloud Run function runtime identity"
}

resource "google_project_iam_member" "function_vertex_ai" {
  project = var.gcp_project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.function.email}"
}

resource "google_service_account" "trigger" {
  project      = var.gcp_project_id
  account_id   = "ticket-analyzer-trigger"
  display_name = "Eventarc identity that invokes the Ticket Analyzer function"
}

resource "google_project_iam_member" "trigger_event_receiver" {
  project = var.gcp_project_id
  role    = "roles/eventarc.eventReceiver"
  member  = "serviceAccount:${google_service_account.trigger.email}"
}

resource "google_cloudfunctions2_function_iam_member" "trigger_can_invoke" {
  project        = var.gcp_project_id
  location       = var.gcp_region
  cloud_function = google_cloudfunctions2_function.ticket_analyzer.name
  role           = "roles/run.invoker"
  member         = "serviceAccount:${google_service_account.trigger.email}"
}

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

  # NOTE: `event_type` and the `event_filters` attribute names below are a
  # best-effort guess for the Managed Kafka event source - I could not verify
  # them against a live project. Before applying, confirm both with:
  #   gcloud eventarc providers describe managedkafka.googleapis.com/Topic \
  #     --location=<region>
  # and adjust `attribute` names/values to match what that command reports.
  event_trigger {
    trigger_region        = var.gcp_region
    event_type            = "google.cloud.managedkafka.topic.v1.messagePublished"
    retry_policy          = "RETRY_POLICY_RETRY"
    service_account_email = google_service_account.trigger.email

    event_filters {
      attribute = "topic"
      value     = google_managed_kafka_topic.support_tickets.topic_id
    }
  }

  depends_on = [
    google_managed_kafka_topic.support_tickets,
    google_project_iam_member.trigger_event_receiver,
  ]

  lifecycle {
    ignore_changes = [build_config[0].source]
  }
}
