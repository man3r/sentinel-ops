import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from agent.models.base import Base


class AuditLog(Base):
    """
    Append-only audit log. Never UPDATE or DELETE rows from this table.
    Each record is SHA-256 hashed and chained with the previous record for tamper-evidence.
    """
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    incident_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Event types: LOG_INGESTION | TRIAGE_DECISION | REASONING_STARTED | RCA_GENERATED |
    #              ALERT_SENT | HUMAN_DECISION | GUARDRAIL_TRIGGERED | MITIGATION_EXECUTED |
    #              JIRA_CREATED | ESCALATION
    actor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    prev_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
