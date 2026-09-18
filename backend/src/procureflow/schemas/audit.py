from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from procureflow.models.audit import ActorType


def _sanitize_actor_string(v: Any) -> str:
    if not v or not isinstance(v, str):
        return "System User"
    if "dev_api_key" in v or v.startswith("procureflow_dev") or v.startswith("sk_") or v.startswith("pk_") or v.startswith("test_key_"):
        return "Development API Principal"
    if "api_key" in v or v.startswith("procureflow_sec"):
        return "Authenticated API Principal"
    return v


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

