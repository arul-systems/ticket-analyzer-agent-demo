import json
from typing import Any, Optional


def extract_ticket_data_from_bytes(raw_value: bytes) -> Optional[dict[str, Any]]:
    """Parse a full ticket record out of a raw Kafka record value. The
    message is expected to be the ticket's JSON object itself (id, subject,
    description, ...). Shared by the local polling consumer and the
    Eventarc-triggered Cloud Run function so both transports agree on the
    wire format."""
    try:
        payload = json.loads(raw_value.decode("utf-8"))
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict) and "id" in payload:
        return payload
    return None
