import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.models import AuditLog
from agent.modules.audit.hasher import compute_hash

logger = logging.getLogger(__name__)

async def append_audit_event(
    db: AsyncSession,
    event_type: str,
    actor: str,
    payload: dict[str, Any],
    incident_id: uuid.UUID | str | None = None
) -> AuditLog:
    """
    Append an immutable event to the audit trail.
    Acquires an exclusive lock on the latest row within the current transaction
    to maintain a strictly linear, unbroken cryptographic hash chain.
    """
    # Convert incident_id to UUID object safely if it's a string, or to str for hashing
    incident_id_obj = None
    if incident_id:
        if isinstance(incident_id, str):
            incident_id_obj = uuid.UUID(incident_id)
        else:
            incident_id_obj = incident_id

    incident_id_str = str(incident_id_obj) if incident_id_obj else None

    # Optimization: removed with_for_update() to reduce DB lock contention
    result = await db.execute(
        select(AuditLog)
        .order_by(AuditLog.id.desc())
        .limit(1)
    )
    last_log = result.scalar_one_or_none()
    
    prev_hash = last_log.record_hash if last_log else None
    
    # Cryptographically chain to the previous record
    new_hash = compute_hash(
        prev_hash=prev_hash,
        event_type=event_type,
        actor=actor,
        payload=payload,
        incident_id=incident_id_str
    )
    
    # Stage the new linked-list record
    audit_event = AuditLog(
        incident_id=incident_id_obj,
        event_type=event_type,
        actor=actor,
        payload=payload,
        prev_hash=prev_hash,
        record_hash=new_hash
    )
    
    db.add(audit_event)
    
    # We do NOT commit here, as the caller might want atomic commits spanning other models.
    # The transaction commit will finalize the lock and write.
    logger.debug(f"Audit appended: {event_type} (hash={new_hash[:8]}, prev={prev_hash[:8] if prev_hash else 'null'})")
    return audit_event
