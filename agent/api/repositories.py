from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.database import get_db
from agent.models import Repository
from agent.schemas import RepositoryCreate, RepositoryResponse

router = APIRouter()


@router.post("", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
async def create_repository(
    repo_in: RepositoryCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register a new Git repository for correlation."""
    # TODO: Store repo_in.token in AWS Secrets Manager -> get secret_arn
    fake_secret_arn = f"arn:aws:secretsmanager:us-east-1:123456789012:secret:{repo_in.name}-abcd"
    
    repo = Repository(
        name=repo_in.name,
        provider=repo_in.provider,
        url=repo_in.url,
        secret_arn=fake_secret_arn
    )
    db.add(repo)
    await db.commit()
    await db.refresh(repo)
    return repo


@router.get("", response_model=list[RepositoryResponse])
async def list_repositories(db: AsyncSession = Depends(get_db)):
    """List all registered repositories."""
    result = await db.execute(select(Repository).order_by(Repository.name))
    return result.scalars().all()
