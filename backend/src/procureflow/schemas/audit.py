from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from procureflow.models.audit import ActorType
from procureflow.utils.actor import sanitize_actor_string as _sanitize_actor_string


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    rfq_id: str
    event_type: str
    actor_type: ActorType
    actor_id: str
    timestamp: datetime
    payload: dict[str, Any] | None = None
    ip_address: str | None = None

    @field_validator("actor_id", mode="before")
    @classmethod
    def sanitize_actor_id(cls, v: Any) -> str:
        return _sanitize_actor_string(v)

