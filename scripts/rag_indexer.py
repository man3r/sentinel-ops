"""
RAG Indexer — Seeds the OpenSearch vector index with runbooks and past incident summaries.
Run once after standing up OpenSearch, or whenever you add new runbooks.

Usage:
    PYTHONPATH=. python scripts/rag_indexer.py
"""
import asyncio
import sys
from pathlib import Path

# Allow running from the project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.modules.reasoning.vector_retrieval import ensure_index_exists, index_document

RUNBOOKS = [
    {
        "id": "runbook-db-connection-pool",
        "title": "Database Connection Pool Exhaustion",
        "text": (
            "Symptoms: 5xx errors on all endpoints; DB timeouts in logs. "
            "Cause: Connection pool exhausted under high concurrency. "
            "Resolution: 1) Scale connection pool size in config. "
            "2) Check for long-running queries holding connections. "
            "3) Add read replicas if write load is high. "
            "4) Enable PgBouncer for connection pooling at the infrastructure level. "
            "Prevention: Set alert on pool utilisation > 80%. Add connection pool load test to CI."
        ),
        "doc_type": "runbook",
    },
    {
        "id": "runbook-oom-killed",
        "title": "OOMKilled Pod Recovery",
        "text": (
            "Symptoms: Kubernetes pod OOMKilled; service unavailable. "
            "Cause: Container memory limit exceeded, typically due to a memory leak or traffic spike. "
            "Resolution: 1) kubectl describe pod <pod> to confirm OOMKilled. "
            "2) Increase memory limit as temporary fix. "
            "3) Profile heap to find leak. "
            "Prevention: Set Prometheus alert on container_memory_usage_bytes > 90% of limit."
        ),
        "doc_type": "runbook",
    },
    {
        "id": "runbook-circuit-breaker-open",
        "title": "Circuit Breaker Open — Downstream API",
        "text": (
            "Symptoms: Service returning 503; circuit breaker state = OPEN in metrics. "
            "Cause: Downstream dependency failing, triggering circuit breaker. "
            "Resolution: 1) Identify failing downstream service from tracing. "
            "2) Check downstream service health. "
            "3) If recoverable, half-open the breaker manually. "
            "4) Enable fallback responses for non-critical paths. "
            "Prevention: Implement retry with exponential backoff + jitter."
        ),
        "doc_type": "runbook",
    },
    {
        "id": "runbook-high-5xx-rate",
        "title": "High 5xx Error Rate — General",
        "text": (
            "Symptoms: Error rate > 5% on core endpoints. "
            "Cause: Could be deployment regression, infra issue, or dependent service failure. "
            "Triage order: 1) Check recent deployments. "
            "2) Check dependency health (DB, cache, third-party APIs). "
            "3) Check resource saturation (CPU, memory, disk). "
            "4) Review last 5 merged PRs for potential regressions. "
            "Resolution: Rollback latest deployment if correlated."
        ),
        "doc_type": "runbook",
    },
    {
        "id": "runbook-kafka-consumer-lag",
        "title": "Kafka Consumer Lag Spike",
        "text": (
            "Symptoms: Consumer lag increasing; downstream processing delayed. "
            "Cause: Consumer throughput reduced (slow processing, crashes, or under-provisioning). "
            "Resolution: 1) Check consumer group status. "
            "2) Scale consumer instances horizontally. "
            "3) Check for poison pill messages causing processing loops. "
            "Prevention: Set alert on consumer lag > 10k messages."
        ),
        "doc_type": "runbook",
    },
    {
        "id": "past-incident-001",
        "title": "Past Incident: Payment Gateway Timeout (2025-11)",
        "text": (
            "Service: payment-service. Severity: SEV1. "
            "Root Cause: Third-party payment processor API latency spike caused synchronous calls "
            "to block the request thread pool. "
            "Resolution: Switched to async non-blocking payment calls + added circuit breaker. "
            "Duration: 22 minutes. Users affected: 840."
        ),
        "doc_type": "past_incident",
    },
    {
        "id": "past-incident-002",
        "title": "Past Incident: DB Connection Exhaustion (2025-09)",
        "text": (
            "Service: user-auth-service. Severity: SEV1. "
            "Root Cause: PR #214 reduced DB connection pool from 100 to 10 in staging config accidentally "
            "promoted to production. "
            "Resolution: Reverted pool config; added config drift detection. "
            "Duration: 11 minutes. Users affected: 2100."
        ),
        "doc_type": "past_incident",
    },
]


async def main() -> None:
    print("Connecting to OpenSearch and ensuring index exists...")
    await ensure_index_exists()

    print(f"Indexing {len(RUNBOOKS)} documents...")
    for doc in RUNBOOKS:
        await index_document(
            doc_id=doc["id"],
            text=doc["text"],
            title=doc["title"],
            doc_type=doc["doc_type"],
        )
        print(f"  ✅ Indexed: {doc['id']}")

    print("\nRAG index seeding complete.")


if __name__ == "__main__":
    asyncio.run(main())
