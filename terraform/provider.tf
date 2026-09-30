terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source = "hashicorp/google"
      # >= 8.3.0 required for google_managed_kafka_cluster's
      # public_cluster_config (added in 8.3.0 - absent through 6.x/7.x/8.0-8.2,
      # confirmed by bisecting the provider's own docs history).
      version = "~> 8.3"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}
