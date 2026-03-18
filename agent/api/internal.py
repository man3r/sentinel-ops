from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from agent.database import get_db
from agent.schemas import IncidentSummary
from agent.models import Incident, AuditLog

router = APIRouter()


@router.post("/incident", status_code=status.HTTP_202_ACCEPTED)
async def trigger_incident(
    incident: IncidentSummary,
    db: AsyncSession = Depends(get_db)
):
    """
    Triggered by Perception Engine when an anomaly is detected.
    This endpoint kicks off the Reasoning Loop for SEV1 and SEV2 incidents.
    """
    # 1. Store the Incident
    new_incident = Incident(
        id=incident.incident_id,
        severity=incident.severity,
        affected_service=incident.affected_service,
        confidence=incident.confidence,
    )
    db.add(new_incident)

    # 2. Write an immutable Audit Log
    audit_event = AuditLog(
        incident_id=new_incident.id,
        event_type="TRIAGE_DECISION",
        actor="PerceptionEngine",
        payload={
            "error_pattern": incident.error_pattern,
            "error_rate_pct": incident.error_rate_pct,
            "sanitized_trace": incident.sanitized_trace,
        },
        record_hash="MOCK_HASH_TO_BE_REPLACED", # Will implement hash chaining later
    )
    db.add(audit_event)
    
    await db.commit()
    
    # 3. Kick off async Reasoning Loop task
    # TODO: asyncio.create_task(run_reasoning_loop(incident.incident_id))
    
    return {
        "incident_id": incident.incident_id,
        "status": "reasoning_loop_triggered" if incident.severity in ("SEV1_CRITICAL", "SEV2_HIGH") else "logged_only",
    }
