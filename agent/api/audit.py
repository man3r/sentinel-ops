import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
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
    format: Optional[str] = Query(None, description="Set to 'json' to download an unpaginated raw JSON array"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Fetch immutable audit logs. Use format=json for downloading compliance bundles."""
    query = select(AuditLog).order_by(AuditLog.id.desc())
    
    if incident_id:
        query = query.where(AuditLog.incident_id == incident_id)
    if actor:
        query = query.where(AuditLog.actor == actor)
    if event_type:
        query = query.where(AuditLog.event_type == event_type)
        
    if format == "json":
        result = await db.execute(query)  # Unpaginated for bundle export
        logs = result.scalars().all()
        # Serialize to plain dicts to bypass Pydantic wrapper for direct raw JSON out
        raw_list = [
            {
                "id": lg.id,
                "incident_id": str(lg.incident_id) if lg.incident_id else None,
                "event_type": lg.event_type,
                "actor": lg.actor,
                "payload": lg.payload,
                "record_hash": lg.record_hash,
                "prev_hash": lg.prev_hash,
                "created_at": lg.created_at.isoformat() if lg.created_at else None,
            }
            for lg in logs
        ]
        return JSONResponse(content=raw_list)

    result = await db.execute(query.limit(limit).offset(offset))
    logs = result.scalars().all()
    
    return {"total": len(logs), "items": logs}
