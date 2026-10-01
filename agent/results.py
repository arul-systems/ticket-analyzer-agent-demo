import json
import logging
from typing import Any

from google.cloud import storage

from agent.config import settings

logger = logging.getLogger(__name__)

_client: storage.Client | None = None


def _get_client() -> storage.Client:
    global _client
    if _client is None:
        _client = storage.Client(project=settings.gcp_project_id)
    return _client


def write_ticket_result(ticket_id: str, result: dict[str, Any]) -> None:
    """Write one JSON file per ticket (named `<ticket_id>.json`) to the
    results bucket. Overwrites if the same ticket is processed again."""
    blob = _get_client().bucket(settings.results_bucket).blob(f"{ticket_id}.json")
    blob.upload_from_string(json.dumps(result, indent=2), content_type="application/json")
    logger.info("Wrote result for ticket %s to gs://%s/%s.json", ticket_id, settings.results_bucket, ticket_id)
