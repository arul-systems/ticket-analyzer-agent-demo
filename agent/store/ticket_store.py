import json
from pathlib import Path
from typing import Any

from agent.config import settings


def _read_all() -> dict[str, dict[str, Any]]:
    path: Path = settings.tickets_store_path
    if not path.exists():
        return {}
    with path.open("r") as f:
        return json.load(f)


def _write_all(tickets: dict[str, dict[str, Any]]) -> None:
    path: Path = settings.tickets_store_path
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(tickets, f, indent=2)


def update_ticket(ticket_id: str, **fields: Any) -> dict[str, Any]:
    """Record the outcome of processing a ticket, keyed by id. Upserts since
    ticket content now arrives fully-formed via the Kafka event rather than
    being pre-seeded here."""
    tickets = _read_all()
    ticket = tickets.get(ticket_id, {"id": ticket_id})
    ticket.update(fields)
    tickets[ticket_id] = ticket
    _write_all(tickets)
    return ticket
