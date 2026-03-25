import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select
from agent.models.rca import RCAReport

async def inspect_rca():
    DATABASE_URL = "postgresql+asyncpg://postgres:localdev@localhost:5432/sentinelops"
    engine = create_async_engine(DATABASE_URL)
    async with AsyncSession(engine) as session:
        result = await session.execute(select(RCAReport).limit(1))
        rca = result.scalar_one_or_none()
        if rca:
            print(f"ID: {rca.id}")
            print(f"Five Whys: {type(rca.five_whys)} - {rca.five_whys}")
            print(f"Action Items: {type(rca.action_items)} - {rca.action_items}")
        else:
            print("No RCA found.")

asyncio.run(inspect_rca())
