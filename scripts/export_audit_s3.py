import asyncio
import json
import logging
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.exceptions import NoCredentialsError
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.config import settings
from agent.database import AsyncSessionLocal
from agent.models import AuditLog

logger = logging.getLogger(__name__)


async def export_to_ndjson() -> None:
    """Read all audit records from the DB and export as .ndjson to AWS S3 (WORM bucket)."""
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"audit_export_{date_str}.ndjson"

    print(f"📦 Fetching audit records to export into {filename}...")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(AuditLog).order_by(AuditLog.id.asc()))
        logs = result.scalars().all()

    if not logs:
        print("ℹ️  No audit records to export.")
        return

    # Write to local temp file
    temp_file = Path(tempfile.gettempdir()) / filename
    with open(temp_file, "w", encoding="utf-8") as f:
        for log in logs:
            record = {
                "id": log.id,
                "incident_id": str(log.incident_id) if log.incident_id else None,
                "event_type": log.event_type,
                "actor": log.actor,
                "payload": log.payload,
                "record_hash": log.record_hash,
                "prev_hash": log.prev_hash,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            f.write(json.dumps(record) + "\n")

    print(f"✅ Local NDJSON generated: {temp_file} ({len(logs)} records)")

    # Upload to S3 WORM bucket if configured
    bucket_name = getattr(settings, "audit_s3_bucket", None)
    
    if bucket_name:
        try:
            s3 = boto3.client("s3")
            s3.upload_file(str(temp_file), bucket_name, f"audit-logs/{filename}")
            print(f"✅ Uploaded to S3: s3://{bucket_name}/audit-logs/{filename}")
        except NoCredentialsError:
            print("⚠️  No AWS credentials found (local dev). File saved locally only.")
        except Exception as e:
            print(f"❌ Failed to upload to S3: {e}")
    else:
        print("ℹ️  AUDIT_S3_BUCKET not set in config. File saved locally only.")


if __name__ == "__main__":
    asyncio.run(export_to_ndjson())
