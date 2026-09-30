"""Entry point for running this agent as a Cloud Run function, instead of
the polling `agent.kafka.listener` consumer.

Eventarc has no native Managed Kafka trigger source (confirmed against a
live project - see terraform/pubsub.tf), so the actual trigger is a Pub/Sub
topic that a Kafka Connect Sink Connector mirrors the Kafka topic into. The
function's trigger/IAM/infra is provisioned by terraform/ (function.tf,
iam.tf, pubsub.tf); code deploys are handled by
.github/workflows/deploy-agent.yml via `gcloud functions deploy`, which
needs the root main.py (re-exports handle_ticket_event) since the gcloud
CLI hard-requires a main.py at the source root for the python312 runtime.

The CloudEvent payload shape handled by `_get_message_bytes` below is a
best-effort match for a Pub/Sub-sourced trigger - verified against a real
Pub/Sub push envelope shape, but not yet exercised by a live trigger.
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
