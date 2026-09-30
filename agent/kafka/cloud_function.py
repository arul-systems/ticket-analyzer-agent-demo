"""Entry point for running this agent as a Cloud Run function triggered by
Eventarc from a Kafka topic (Google Cloud Managed Service for Apache Kafka,
or Confluent Cloud), instead of the polling `agent.kafka.listener` consumer.

Deploy with, e.g.:

    gcloud run deploy ticket-analyzer-agent \\
        --source . \\
        --function agent.kafka.cloud_function.handle_ticket_event \\
        --region REGION \\
        --no-allow-unauthenticated

    gcloud eventarc triggers create ticket-analyzer-kafka-trigger \\
        --location=REGION \\
        --destination-run-service=ticket-analyzer-agent \\
        --destination-run-region=REGION \\
        --event-filters="type=google.cloud.managedkafka.topic.v1.messagePublished" \\
        --event-filters="topic=TOPIC_ID" \\
        --service-account=SERVICE_ACCOUNT_EMAIL

NOTE: verify the exact `--event-filters type=...` value and the CloudEvent
payload shape handled by `_get_message_bytes` below against the current
Eventarc + Managed Service for Apache Kafka documentation before deploying -
this is a fast-moving GA surface and field/type names may have changed.
"""

import base64
import json
import logging

import functions_framework
from cloudevents.http import CloudEvent

from agent.kafka.parsing import extract_ticket_data_from_bytes
from agent.processor import process_ticket

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def _get_message_bytes(cloud_event: CloudEvent) -> bytes:
    """Best-effort extraction of the raw Kafka record value from an Eventarc
    CloudEvent. Handles the schema variants that are plausible for a Kafka
    source (a raw byte/string payload, a Pub/Sub-style nested envelope, or a
    flat dict with a base64 `data`/`value` field)."""
    data = cloud_event.data
    if isinstance(data, (bytes, bytearray)):
        return bytes(data)
    if isinstance(data, str):
        return data.encode("utf-8")
    if isinstance(data, dict):
        nested = data.get("message")
        if isinstance(nested, dict) and "data" in nested:
            return base64.b64decode(nested["data"])
        for key in ("data", "value"):
            value = data.get(key)
            if isinstance(value, str):
                return base64.b64decode(value)
        return json.dumps(data).encode("utf-8")
    raise ValueError(f"Unrecognized CloudEvent data shape: {type(data)!r}")


@functions_framework.cloud_event
def handle_ticket_event(cloud_event: CloudEvent) -> None:
    try:
        raw = _get_message_bytes(cloud_event)
    except ValueError:
        logger.exception("Could not extract message bytes from CloudEvent")
        return

    ticket_data = extract_ticket_data_from_bytes(raw)
    if not ticket_data:
        logger.warning("Skipping event with no parseable ticket data: %r", raw)
        return

    ticket_id = ticket_data.get("id")
    logger.info("Received ticket via Eventarc: %s", ticket_id)
    try:
        process_ticket(ticket_data)
    except Exception:
        logger.exception("Failed to process ticket %s", ticket_id)
