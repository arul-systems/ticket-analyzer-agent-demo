from typing import Literal, Optional

from pydantic import BaseModel

Priority = Literal["Low", "Medium", "High", "Critical"]
Team = Literal["Engineering", "Billing", "Customer Success", "Security", "Support Tier 2"]
TicketStatus = Literal["open", "resolved", "assigned", "closed_not_supported"]


class Ticket(BaseModel):
    id: str
    subject: str
    description: str
    customer: str
    customer_tier: str
    product: str
    category: str
    channel: str
    created_at: str
    status: TicketStatus
    priority: Optional[Priority] = None
    resolution: Optional[str] = None
