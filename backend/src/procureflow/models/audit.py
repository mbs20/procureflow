import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column

from procureflow.database import Base


class ActorType(str, Enum):
    USER = "user"
    SYSTEM = "system"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rfq_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rfqs.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_type: Mapped[ActorType] = mapped_column(
        SQLEnum(ActorType), default=ActorType.USER, nullable=False
    )
    actor_id: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    __table_args__ = (Index("idx_audit_rfq_time", "rfq_id", "timestamp"),)
