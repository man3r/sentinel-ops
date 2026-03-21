import asyncio
import sys
from pathlib import Path

# Provide absolute imports for running as script
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from agent.database import AsyncSessionLocal
from agent.models import AuditLog
from agent.modules.audit.hasher import compute_hash


async def main() -> None:
    print("🔍 Fetching full audit chain from PostgreSQL...")

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AuditLog).order_by(AuditLog.id.asc())
        )
        logs = result.scalars().all()

    if not logs:
        print("ℹ️  No audit records found in the database.")
        return

    print(f"📦 Found {len(logs)} audit records. Verifying cryptographic chain...")

    prev_hash_expected = None
    errors = 0

    for i, log in enumerate(logs):
        # 1. Check link to previous record
        if log.prev_hash != prev_hash_expected:
            print(f"❌ ERROR at Record {log.id}: Broken chain link!")
            print(f"   Expected prev_hash: {prev_hash_expected}")
            print(f"   Actual prev_hash:   {log.prev_hash}")
            errors += 1

        # 2. Recompute own hash to verify payload integrity
        incident_id_str = str(log.incident_id) if log.incident_id else None
        
        computed = compute_hash(
            prev_hash=log.prev_hash,
            event_type=log.event_type,
            actor=log.actor,
            payload=log.payload,
            incident_id=incident_id_str,
        )

        if computed != log.record_hash:
            print(f"❌ ERROR at Record {log.id}: Payload tampering detected!")
            print(f"   Expected hash: {log.record_hash}")
            print(f"   Computed hash: {computed}")
            errors += 1

        prev_hash_expected = log.record_hash

    if errors == 0:
        print(f"\n✅ All {len(logs)} audit records verified. Chain intact.")
    else:
        print(f"\n🚨 VERIFICATION FAILED. Found {errors} chain violations.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
