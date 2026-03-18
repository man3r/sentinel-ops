from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.database import get_db
from agent.models import GuardrailRule
from agent.schemas import GuardrailCreate, GuardrailResponse

router = APIRouter()


@router.post("", response_model=GuardrailResponse, status_code=status.HTTP_201_CREATED)
async def create_guardrail(
    rule_in: GuardrailCreate,
    db: AsyncSession = Depends(get_db)
):
    """Add a new NO_GO_ZONE or update CONFIDENCE_THRESHOLD."""
    rule = GuardrailRule(
        rule_type=rule_in.rule_type,
        value=rule_in.value,
        description=rule_in.description
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.get("", response_model=list[GuardrailResponse])
async def list_guardrails(db: AsyncSession = Depends(get_db)):
    """List all active guardrail rules."""
    result = await db.execute(select(GuardrailRule).where(GuardrailRule.active == True))
    return result.scalars().all()
