import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.database import get_db
from agent.models import AuditLog
from agent.schemas import AuditListResponse

router = APIRouter()


@router.get("", response_model=AuditListResponse)
async def list_audit_logs(
    incident_id: Optional[uuid.UUID] = None,
    actor: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Fetch immutable audit logs, optionally filtered by incident, actor, or event type."""
    query = select(AuditLog).order_by(AuditLog.id.desc())
    
    if incident_id:
        query = query.where(AuditLog.incident_id == incident_id)
    if actor:
        query = query.where(AuditLog.actor == actor)
    if event_type:
        query = query.where(AuditLog.event_type == event_type)
        
    result = await db.execute(query.limit(limit).offset(offset))
    logs = result.scalars().all()
    
    return {"total": len(logs), "items": logs}
