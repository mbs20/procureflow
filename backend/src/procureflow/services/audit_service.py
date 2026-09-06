from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from procureflow.models.audit import ActorType, AuditLog


async def record_audit_event(
    db: AsyncSession,
    rfq_id: str,
    event_type: str,
    payload: dict[str, Any] | None = None,
    actor_id: str = "system",
    actor_type: ActorType = ActorType.USER,
    ip_address: str | None = None,
) -> AuditLog:
    """Record an append-only audit log entry."""
    audit_entry = AuditLog(
        rfq_id=rfq_id,
        event_type=event_type,
        actor_type=actor_type,
        actor_id=actor_id,
        payload=payload,
        ip_address=ip_address,
    )
    db.add(audit_entry)
    await db.flush()
    return audit_entry
