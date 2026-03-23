"""
Mitigation Executor — dispatches approved human actions.

Supported actions:
  - approve_rollback : Logs that a rollback was approved. (Actual k8s/deploy call is Phase 6)
  - create_jira      : Creates a Jira issue from the RCA (stub in Phase 3; real API in Phase 3b)
  - dismiss          : Marks the incident as resolved without further action
  - escalate         : Bumps severity and re-pages
"""
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.models import Incident, RCAReport
from agent.modules.audit.logger import append_audit_event

logger = logging.getLogger(__name__)


async def handle(
    action_id: str,
    incident_id: str,
    actor: str,
    db: AsyncSession,
) -> dict:
    """
    Execute the approved action after guardrails have passed.
    Writes HUMAN_DECISION + MITIGATION_EXECUTED audit events.
    Returns a dict with `message` for Slack response.
    """
    result = await db.execute(
        select(Incident).where(Incident.id == uuid.UUID(incident_id))
    )
    incident = result.scalar_one_or_none()
    if not incident:
        return {"message": f"❌ Incident `{incident_id}` not found."}

    rca_result = await db.execute(
        select(RCAReport).where(RCAReport.incident_id == incident.id)
    )
    rca = rca_result.scalar_one_or_none()

    # ── HUMAN_DECISION audit ───────────────────────────────────────────────────
    await append_audit_event(
        db=db,
        incident_id=incident.id,
        event_type="HUMAN_DECISION",
        actor=actor,
        payload={"action": action_id, "incident_id": incident_id}
    )

    # ── Dispatch action ────────────────────────────────────────────────────────
    if action_id == "approve_rollback":
        return await _approve_rollback(incident, rca, actor, db)

    elif action_id == "create_jira":
        return await _create_jira(incident, rca, actor, db)

    elif action_id == "dismiss":
        return await _dismiss(incident, actor, db)

    else:
        logger.warning(f"Unknown action_id: {action_id}")
        return {"message": f"❓ Unknown action `{action_id}`."}


async def _approve_rollback(incident: Incident, rca: RCAReport | None, actor: str, db: AsyncSession) -> dict:
    """Execute physical git revert and mark incident as resolved."""
    import subprocess
    
    rollback_status = "Skipped (No causal commit)"
    git_output = ""
    
    if incident.causal_commit:
        try:
            # We use --no-edit to avoid interactive editor popups
            # The agent assumes it is running in the context of the repository it is managing
            cmd = ["git", "revert", "--no-edit", incident.causal_commit]
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.returncode == 0:
                rollback_status = "Success"
                git_output = process.stdout
            else:
                rollback_status = f"Failed (Exit {process.returncode})"
                git_output = process.stderr
        except Exception as e:
            rollback_status = "Error"
            git_output = str(e)

    incident.status = "RESOLVED"

    await append_audit_event(
        db=db,
        incident_id=incident.id,
        event_type="MITIGATION_EXECUTED",
        actor=actor,
        payload={
            "action": "approve_rollback",
            "causal_commit": incident.causal_commit,
            "causal_repo": incident.causal_repo,
            "rollback_status": rollback_status,
            "git_output": git_output[:500]
        }
    )
    await db.commit()

    logger.info(f"✅ Rollback {rollback_status} for incident {incident.id} by {actor}")
    
    status_emoji = "✅" if rollback_status == "Success" else "⚠️" if rollback_status == "Skipped (No causal commit)" else "❌"
    
    return {
        "message": (
            f"{status_emoji} *Rollback {rollback_status}* by `{actor}`.\n"
            f"Target: `{incident.causal_commit or 'none'}`\n"
            f"```\n{git_output[:200] if git_output else 'No git output.'}\n```\n"
            f"_Incident status → RESOLVED._"
        )
    }


async def _create_jira(incident: Incident, rca: RCAReport | None, actor: str, db: AsyncSession) -> dict:
    """Create a Jira issue (stub — real Jira API call wired in Phase 3b)."""
    root_cause = rca.root_cause if rca else "RCA pending"
    jira_key = f"SENTINEL-{str(incident.id)[:8].upper()}"  # Stub ticket key

    await append_audit_event(
        db=db,
        incident_id=incident.id,
        event_type="MITIGATION_EXECUTED",
        actor=actor,
        payload={
            "action": "create_jira",
            "jira_key": jira_key,
            "root_cause": root_cause,
            "note": "Real Jira API integration wired in Phase 3b.",
        }
    )
    await db.commit()

    logger.info(f"📋 Jira ticket {jira_key} created for incident {incident.id} by {actor}")
    return {
        "message": (
            f"📋 *Jira ticket created:* `{jira_key}`\n"
            f"*Root Cause:* {root_cause[:200]}\n"
            f"_Created by `{actor}`._"
        )
    }


async def _dismiss(incident: Incident, actor: str, db: AsyncSession) -> dict:
    """Dismiss the incident — marks it RESOLVED with no automated action."""
    incident.status = "RESOLVED"

    await append_audit_event(
        db=db,
        incident_id=incident.id,
        event_type="MITIGATION_EXECUTED",
        actor=actor,
        payload={"action": "dismiss", "note": "Manually dismissed by engineer."}
    )
    await db.commit()

    logger.info(f"🔕 Incident {incident.id} dismissed by {actor}")
    return {
        "message": (
            f"🔕 *Incident dismissed* by `{actor}`.\n"
            f"_No automated action taken. Incident status → RESOLVED._"
        )
    }
