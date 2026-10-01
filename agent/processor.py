import json
import logging
from typing import Any

from agent.graph import build_agent

logger = logging.getLogger(__name__)

_agent = None


def _get_agent():
    global _agent
    if _agent is None:
        _agent = build_agent()
    return _agent


def process_ticket(ticket_data: dict[str, Any]) -> str:
    """Run the triage agent for a single ticket and return its final text
    summary. The full ticket record is embedded directly in the prompt, so
    the agent never needs to look it up. Side effects (priority/status/
    resolution) are written to the ticket store by whichever terminal tool
    the agent calls."""
    agent = _get_agent()
    ticket_id = ticket_data.get("id", "unknown")
    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "A new support ticket needs triage. Here is the full "
                        f"ticket record as JSON:\n{json.dumps(ticket_data)}"
                    ),
                }
            ]
        }
    )

    final_message = result["messages"][-1]
    summary = final_message.content
    logger.info("Processed ticket %s: %s", ticket_id, summary)
    return summary
