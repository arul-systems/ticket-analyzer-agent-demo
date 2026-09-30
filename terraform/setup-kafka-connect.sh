#!/usr/bin/env bash
# Provisions the Kafka Connect cluster + Pub/Sub Sink Connector that bridges
# the support-tickets Kafka topic into the ticket-events Pub/Sub topic (see
# pubsub.tf for why: Eventarc has no native Managed Kafka trigger source).
#
# Not Terraform: as of this writing there is no google_managed_kafka_connect_cluster
# or google_managed_kafka_connector resource in the hashicorp/google provider
# (checked against the live provider schema), so this has to be run by hand -
# after `terraform apply` has created the Kafka cluster and Pub/Sub topic,
# and after the Kafka cluster shows STATE=ACTIVE (`gcloud managed-kafka
# clusters list`).
#
# NOTE: `connector.class=com.google.pubsub.kafka.sink.CloudPubSubSinkConnector`
# is inferred by symmetry with the *source* connector class Google's own
# `gcloud managed-kafka connectors create --help` example uses
# (com.google.pubsub.kafka.source.CloudPubSubSourceConnector) - it was not
# directly confirmed against a live connect cluster. If connector creation
# fails with an unknown-class error, check
# `gcloud managed-kafka connect-clusters describe` or Google's
# pubsub-group-kafka-connector docs for the exact bundled class name.

set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:?set GCP_PROJECT_ID}"
REGION="${GCP_REGION:-us-central1}"
KAFKA_CLUSTER="ticket-analyzer-kafka"
CONNECT_CLUSTER="ticket-analyzer-connect"
CONNECTOR="pubsub-sink"
KAFKA_TOPIC="support-tickets"
PUBSUB_TOPIC="ticket-events"
SUBNET="projects/${PROJECT_ID}/regions/${REGION}/subnetworks/default"

gcloud managed-kafka connect-clusters create "$CONNECT_CLUSTER" \
  --project="$PROJECT_ID" \
  --location="$REGION" \
  --cpu=3 \
  --memory=3GiB \
  --primary-subnet="$SUBNET" \
  --kafka-cluster="$KAFKA_CLUSTER"

echo "Waiting for connect cluster to become ACTIVE (this can take a while)..."
gcloud managed-kafka connect-clusters describe "$CONNECT_CLUSTER" \
  --project="$PROJECT_ID" --location="$REGION"

gcloud managed-kafka connectors create "$CONNECTOR" \
  --project="$PROJECT_ID" \
  --location="$REGION" \
  --connect-cluster="$CONNECT_CLUSTER" \
  --configs="connector.class=com.google.pubsub.kafka.sink.CloudPubSubSinkConnector,topics=${KAFKA_TOPIC},cps.project=${PROJECT_ID},cps.topic=${PUBSUB_TOPIC},key.converter=org.apache.kafka.connect.converters.ByteArrayConverter,value.converter=org.apache.kafka.connect.converters.ByteArrayConverter,tasks.max=1"
