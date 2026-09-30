import logging

from langchain_core.tools import tool

from agent.models import Priority, Team

logger = logging.getLogger(__name__)


@tool
def auto_resolve_ticket(ticket_id: str, priority: Priority, resolution_summary: str) -> str:
    """Resolve the ticket automatically without human involvement. Use this only
    for well-understood, self-service issues (e.g. how-to questions, known
    workarounds, password/account access instructions) where you can give the
    customer a complete, correct resolution yourself. `resolution_summary` must
    contain the actual steps/answer sent to the customer, not just a note."""
    logger.info(
        "Ticket %s auto-resolved. priority=%s resolution=%s",
        ticket_id,
        priority,
        resolution_summary,
    )
    return f"Ticket {ticket_id} auto-resolved with priority {priority}."


@tool
def assign_ticket(ticket_id: str, priority: Priority, team: Team, reason: str) -> str:
    """Assign the ticket to a human team for further investigation or action.
    Use this when the issue requires human judgement, access to internal
    systems, or is account/environment specific (bugs, billing disputes,
    security incidents, complex integration questions)."""
    logger.info(
        "Ticket %s assigned to %s. priority=%s reason=%s",
        ticket_id,
        team,
        priority,
        reason,
    )
    return f"Ticket {ticket_id} assigned to {team} with priority {priority}."


@tool
def close_as_not_supported(ticket_id: str, priority: Priority, reason: str) -> str:
    """Close the ticket as not supported. Use this when the request is about a
    product, feature, platform, or integration that is explicitly out of
    scope/unsupported, or is spam/not actionable."""
    logger.info(
        "Ticket %s closed as not supported. priority=%s reason=%s",
        ticket_id,
        priority,
        reason,
    )
    return f"Ticket {ticket_id} closed as not supported with priority {priority}."


ALL_TOOLS = [auto_resolve_ticket, assign_ticket, close_as_not_supported]
