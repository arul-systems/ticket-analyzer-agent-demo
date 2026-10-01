variable "gcp_project_id" {
  description = "GCP project that hosts the Pub/Sub topic and Cloud Run function."
  type        = string
}

variable "gcp_region" {
  description = "Region for the Cloud Run function and its Eventarc trigger."
  type        = string
  default     = "us-central1"
}
