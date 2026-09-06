from datetime import datetime
from typing import Any

from pydantic import BaseModel

from procureflow.models.audit import ActorType


class AuditLogRead(BaseModel):
    id: str
    rfq_id: str
    event_type: str
    actor_type: ActorType
    actor_id: str
    timestamp: datetime
    payload: dict[str, Any] | None = None
    ip_address: str | None = None

    class Config:
        from_attributes = True
