"""Entry point for running this agent as a Cloud Run function. This is the
only way it runs - there's no local broker or standalone consumer process in
this project.

A ticket is published directly to the `support-tickets` Pub/Sub topic (see
scripts/produce_test_ticket.py), and Eventarc pushes it here. The
function's trigger/IAM/infra is provisioned by terraform/ (function.tf,
iam.tf, pubsub.tf); code deploys are handled by
.github/workflows/deploy-agent.yml via `gcloud functions deploy`, which
needs the root main.py (re-exports handle_ticket_event) since the gcloud
CLI hard-requires a main.py at the source root for the python312 runtime.
"""

import base64
import logging

import functions_framework
from cloudevents.http import CloudEvent

from agent.parsing import extract_ticket_data_from_bytes
from agent.processor import process_ticket

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

def _extract_ticket_data_from_bytes(raw_value: bytes) -> Optional[dict[str, Any]]:
    """Parse a full ticket record out of a raw Pub/Sub message body. The
    message is expected to be the ticket's JSON object itself (id, subject,
    description, ...)."""
    try:
        payload = json.loads(raw_value.decode("utf-8"))
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict) and "id" in payload:
        return payload
    return None

@functions_framework.cloud_event
def handle_ticket_event(cloud_event: CloudEvent) -> None:
    try:
        raw = base64.b64decode(cloud_event.data["message"]["data"])
    except (KeyError, TypeError, ValueError):
        logger.exception("Could not extract message bytes from CloudEvent")
        return

    ticket_data = _extract_ticket_data_from_bytes(raw)
    if not ticket_data:
        logger.warning("Skipping event with no parseable ticket data: %r", raw)
        return

    ticket_id = ticket_data.get("id")
    logger.info("Received ticket via Eventarc: %s", ticket_id)
    try:
        process_ticket(ticket_data)
    except Exception:
        logger.exception("Failed to process ticket %s", ticket_id)
