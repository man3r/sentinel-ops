import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.database import get_db
from agent.models import Incident, RCAReport
from agent.schemas import IncidentListResponse, IncidentResponse, RCAResponse

router = APIRouter()


@router.get("", response_model=IncidentListResponse)
async def list_incidents(
    severity: Optional[str] = Query(None, description="Filter by SEV1_CRITICAL, SEV2_HIGH, etc."),
    status_filter: Optional[str] = Query(None, alias="status", description="OPEN, ACKNOWLEDGED, RESOLVED"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """List all incidents, for the admin dashboard."""
    query = select(Incident).order_by(Incident.created_at.desc())
    
    if severity:
        query = query.where(Incident.severity == severity)
    if status_filter:
        query = query.where(Incident.status == status_filter)
        
    # TODO: Add pagination counts properly
    result = await db.execute(query.limit(limit).offset(offset))
    incidents = result.scalars().all()
    
    return {"total": len(incidents), "items": incidents}


@router.get("/{incident_id}/rca", response_model=RCAResponse)
async def get_incident_rca(
    incident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get the full Root Cause Analysis report for a specific incident."""
    query = select(RCAReport).where(RCAReport.incident_id == incident_id)
    result = await db.execute(query)
    rca = result.scalar_one_or_none()
    
    if not rca:
        raise HTTPException(status_code=404, detail="RCA not found for this incident")
        
    return rca
