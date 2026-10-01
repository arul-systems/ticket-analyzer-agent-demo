data "google_project" "current" {
  project_id = var.gcp_project_id
}

# --- Function runtime identity ---

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

# --- Eventarc trigger identity ---

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

# roles/run.invoker has to be granted on the function's underlying Cloud Run
# service (run.googleapis.com), not through the Cloud Functions IAM surface -
# granting it via google_cloudfunctions2_function_iam_member fails with a
# generic "Invalid argument" 400 (confirmed against a live project). Gen2
# functions name their backing Cloud Run service identically to the function,
# so the same short name is reused here.
resource "google_cloud_run_v2_service_iam_member" "trigger_can_invoke" {
  project  = var.gcp_project_id
  location = var.gcp_region
  name     = google_cloudfunctions2_function.ticket_analyzer.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.trigger.email}"
}

# --- Eventarc <- Pub/Sub trigger IAM (see pubsub.tf for the topic itself) ---

# Pub/Sub-sourced Eventarc triggers invoke Cloud Run via a Pub/Sub push
# subscription, which mints an OIDC token as the trigger's service account.
# That requires Pub/Sub's own service agent to be able to impersonate it.
resource "google_service_account_iam_member" "pubsub_can_mint_trigger_tokens" {
  service_account_id = google_service_account.trigger.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

# --- CI deployer identity (used by .github/workflows/deploy-agent.yml) ---

resource "google_service_account" "ci_deployer" {
  project      = var.gcp_project_id
  account_id   = "ticket-analyzer-ci"
  display_name = "GitHub Actions deployer for ticket-analyzer-agent"
}

resource "google_project_iam_member" "ci_deployer_cloudfunctions" {
  project = var.gcp_project_id
  role    = "roles/cloudfunctions.developer"
  member  = "serviceAccount:${google_service_account.ci_deployer.email}"
}

# Per Google's own Cloud Functions IAM docs: deploying requires Service
# Account User on both the runtime service account and the Cloud Build
# service account, not just cloudfunctions.developer.
resource "google_service_account_iam_member" "ci_deployer_acts_as_function" {
  service_account_id = google_service_account.function.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.ci_deployer.email}"
}

# Google's generic docs call this "the Cloud Build service account," but
# checked against this project's actual function in state
# (build_config[0].service_account) it's the Compute Engine default SA, not
# the classic {number}@cloudbuild.gserviceaccount.com - GCP has been
# defaulting newer projects' build steps to the Compute default SA.
resource "google_service_account_iam_member" "ci_deployer_acts_as_build_sa" {
  service_account_id = "projects/${var.gcp_project_id}/serviceAccounts/${data.google_project.current.number}-compute@developer.gserviceaccount.com"
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.ci_deployer.email}"
}

# Redeploying a function with an existing Eventarc trigger re-submits the
# trigger's service_account_email too, so the deployer needs Service Account
# User on it as well - confirmed via a live 403 from `gcloud functions
# deploy` naming exactly this SA (Google's generic docs only mention the
# runtime and build service accounts).
resource "google_service_account_iam_member" "ci_deployer_acts_as_trigger" {
  service_account_id = google_service_account.trigger.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.ci_deployer.email}"
}

# --no-allow-unauthenticated makes `gcloud functions deploy` manage the
# underlying Cloud Run service's IAM policy directly (to keep it non-public),
# which needs run.services.setIamPolicy - not included in
# roles/cloudfunctions.developer (confirmed via `gcloud iam roles describe`;
# it has run.services.getIamPolicy but not the set variant), and surfaced as
# a live 403 from a real deploy. Scoped to just this Cloud Run service rather
# than project-wide roles/run.admin.
resource "google_cloud_run_v2_service_iam_member" "ci_deployer_manages_service_iam" {
  project  = var.gcp_project_id
  location = var.gcp_region
  name     = google_cloudfunctions2_function.ticket_analyzer.name
  role     = "roles/run.admin"
  member   = "serviceAccount:${google_service_account.ci_deployer.email}"
}
