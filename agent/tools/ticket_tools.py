import json

from langchain_core.tools import tool

from agent.models import Priority, Team
from agent.store import ticket_store


@tool
def auto_resolve_ticket(ticket_id: str, priority: Priority, resolution_summary: str) -> str:
    """Resolve the ticket automatically without human involvement. Use this only
    for well-understood, self-service issues (e.g. how-to questions, known
    workarounds, password/account access instructions) where you can give the
    customer a complete, correct resolution yourself. `resolution_summary` must
    contain the actual steps/answer sent to the customer, not just a note."""
    ticket = ticket_store.update_ticket(
        ticket_id,
        status="resolved",
        priority=priority,
        resolution=resolution_summary,
    )
    return f"Ticket {ticket_id} auto-resolved with priority {priority}. Ticket: {json.dumps(ticket)}"


@tool
def assign_ticket(ticket_id: str, priority: Priority, team: Team, reason: str) -> str:
    """Assign the ticket to a human team for further investigation or action.
    Use this when the issue requires human judgement, access to internal
    systems, or is account/environment specific (bugs, billing disputes,
    security incidents, complex integration questions)."""
    ticket = ticket_store.update_ticket(
        ticket_id,
        status="assigned",
        priority=priority,
        resolution=f"Assigned to {team}: {reason}",
    )
    return f"Ticket {ticket_id} assigned to {team} with priority {priority}. Ticket: {json.dumps(ticket)}"


@tool
def close_as_not_supported(ticket_id: str, priority: Priority, reason: str) -> str:
    """Close the ticket as not supported. Use this when the request is about a
    product, feature, platform, or integration that is explicitly out of
    scope/unsupported, or is spam/not actionable."""
    ticket = ticket_store.update_ticket(
        ticket_id,
        status="closed_not_supported",
        priority=priority,
        resolution=reason,
    )
    return f"Ticket {ticket_id} closed as not supported with priority {priority}. Ticket: {json.dumps(ticket)}"


ALL_TOOLS = [auto_resolve_ticket, assign_ticket, close_as_not_supported]
