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


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Fetch details of a specific incident."""
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    return incident


@router.get("/{incident_id}/rca", response_model=RCAResponse)
async def get_incident_rca(
    incident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get the full Root Cause Analysis report for a specific incident."""
    # We join with the Parent Incident to fetch causal commit/repo info 
    # which is required by the RCAResponse schema.
    query = (
        select(RCAReport, Incident.causal_commit, Incident.causal_repo)
        .join(Incident, Incident.id == RCAReport.incident_id)
        .where(RCAReport.incident_id == incident_id)
    )
    result = await db.execute(query)
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="RCA not found for this incident")
        
    rca, causal_commit, causal_repo = row
    # Temporarily set the fields to populate the Pydantic schema
    rca.causal_commit = causal_commit
    rca.causal_repo = causal_repo
    
    return rca
@router.get("/spend/tokens")
async def get_token_spend(db: AsyncSession = Depends(get_db)):
    """Fetch time-series token spend for dashboard."""
    query = select(RCAReport.created_at, RCAReport.bedrock_tokens).where(RCAReport.bedrock_tokens > 0).order_by(RCAReport.created_at.asc())
    result = await db.execute(query)
    
    return [
        {"timestamp": rca.created_at.isoformat(), "tokens": rca.bedrock_tokens}
        for rca in result.all()
    ]
