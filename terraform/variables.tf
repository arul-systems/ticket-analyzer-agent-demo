variable "gcp_project_id" {
  description = "GCP project that hosts the Managed Service for Apache Kafka cluster."
  type        = string
}

variable "gcp_region" {
  description = "Region for the Kafka cluster. Managed Service for Apache Kafka is only available in a subset of regions - verify yours is supported before applying."
  type        = string
  default     = "us-central1"
}
