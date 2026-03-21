"""
Bedrock Client — invokes Claude 3.5 Sonnet to generate structured, schema-validated RCA JSON.
Falls back to a deterministic MOCK RCA when Bedrock is unavailable (local dev without AWS creds).
"""
import json
import logging
from typing import Any

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from agent.config import settings

logger = logging.getLogger(__name__)


# ── RCA Fallback (local dev mock) ──────────────────────────────────────────────

MOCK_RCA: dict[str, Any] = {
    "root_cause": "Database connection pool exhausted due to a misconfigured timeout value. Connections were held open longer than expected under peak load.",
    "causal_commit": None,
    "causal_repo": None,
    "causal_pr": None,
    "five_whys": [
        {"why": 1, "question": "Why did the service return 5xx errors?", "answer": "The service could not acquire a database connection."},
        {"why": 2, "question": "Why could it not acquire a connection?", "answer": "The connection pool was fully exhausted."},
        {"why": 3, "question": "Why was the pool exhausted?", "answer": "Too many concurrent requests were holding connections open longer than expected."},
        {"why": 4, "question": "Why were connections held open longer?", "answer": "The DB query timeout was reduced in a recent configuration change."},
        {"why": 5, "question": "Why was the timeout reduced without proper review?", "answer": "The change was made in a PR without a load-test gate to validate connection pool behaviour under concurrency."},
    ],
    "impact_analysis": {
        "affected_users": 0,
        "stalled_transactions": 0,
        "revenue_at_risk": "Under assessment",
        "duration_minutes": 0,
    },
    "action_items": {
        "corrective_actions": [
            {"action": "Restore previous DB connection pool timeout configuration immediately.", "owner": "on-call-engineer", "due_date": "immediate", "status": "Open"},
        ],
        "preventive_actions": [
            {"action": "Add connection pool concurrency test to CI pipeline.", "owner": "platform-team", "due_date": "next-sprint", "status": "Open"},
            {"action": "Set alerting threshold on pool utilisation > 80%.", "owner": "sre-team", "due_date": "next-sprint", "status": "Open"},
        ],
        "systemic_actions": [
            {"action": "Formalise DB configuration change review checklist.", "owner": "engineering-manager", "due_date": "next-quarter", "status": "Open"},
        ],
    },
}


# ── Prompt Builder ─────────────────────────────────────────────────────────────

def _build_rca_prompt(
    incident: dict[str, Any],
    rag_context: list[dict[str, Any]],
    git_prs: list[dict[str, Any]],
) -> str:
    rag_text = "\n".join(
        [f"  [{i+1}] ({r.get('doc_type','?')}) {r.get('title','')}: {r.get('text','')[:400]}" for i, r in enumerate(rag_context)]
    ) or "  No similar incidents found in knowledge base."

    git_text = "\n".join(
        [f"  - PR #{p['number']} '{p['title']}' by @{p['author']} merged {p['merged_at']} (repo: {p['repo']})" for p in git_prs]
    ) or "  No recent PRs in the correlation window."

    return f"""System: You are SentinelOps, a Senior SRE agent.
You have been given an incident report, historical context, and recent Git activity.
Your job is to produce a structured RCA in JSON.

## Incident
Service:       {incident.get('affected_service', 'unknown')}
Severity:      {incident.get('severity', 'unknown')}
Error Pattern: {incident.get('error_pattern', 'unknown')}
Error Rate:    {incident.get('error_rate_pct', 'N/A')}%
Sanitized Trace (excerpt):
{str(incident.get('sanitized_trace', ''))[:1500]}

## Historical Context (similar past incidents / runbooks)
{rag_text}

## Recent Git Activity (merged in last 24h across all registered repos)
{git_text}

## Instructions
Return ONLY a valid JSON object with these exact keys:
- root_cause: string (one clear sentence identifying the root cause)
- causal_commit: string | null (git commit SHA if identifiable, else null)
- causal_repo: string | null (repository name if identifiable, else null)
- causal_pr: integer | null (PR number if identifiable, else null)
- five_whys: array of exactly 5 objects with keys: why (int 1-5), question (str), answer (str)
- impact_analysis: object with keys: affected_users (int), stalled_transactions (int), revenue_at_risk (str), duration_minutes (int)
- action_items: object with keys:
    corrective_actions: array of {{action, owner, due_date, status}} (fix NOW)
    preventive_actions: array of {{action, owner, due_date, status}} (prevent recurrence)
    systemic_actions: array of {{action, owner, due_date, status}} (address systemic gaps)

Return ONLY valid JSON. No markdown. No explanation."""


# ── Main Bedrock Invocation ────────────────────────────────────────────────────

async def generate_rca(
    incident: dict[str, Any],
    rag_context: list[dict[str, Any]],
    git_prs: list[dict[str, Any]],
) -> tuple[dict[str, Any], int | None]:
    """
    Call Claude 3.5 Sonnet on Bedrock to generate a structured RCA.
    Returns: (rca_dict, bedrock_token_count)

    Falls back to MOCK_RCA gracefully in local dev (no AWS creds needed).
    """
    prompt = _build_rca_prompt(incident, rag_context, git_prs)

    try:
        client = boto3.client("bedrock-runtime", region_name=settings.aws_region)
        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2048,
                "temperature": 0.1,  # Low temp for deterministic structured JSON
                "messages": [{"role": "user", "content": prompt}],
            }
        )
        response = client.invoke_model(modelId=settings.bedrock_model_id, body=body)
        result = json.loads(response["body"].read())
        content = result["content"][0]["text"].strip()
        tokens = result.get("usage", {}).get("output_tokens", 0)

        # Strip markdown code fences if model wraps its response
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        rca = json.loads(content)
        logger.info(f"✅ Bedrock RCA generated ({tokens} output tokens)")
        return rca, tokens

    except NoCredentialsError:
        logger.warning("No AWS credentials found — using MOCK RCA (local dev mode).")
    except ClientError as e:
        logger.warning(f"Bedrock ClientError ({e.response['Error']['Code']}) — using MOCK RCA.")
    except json.JSONDecodeError as e:
        logger.error(f"Bedrock returned non-JSON response: {e} — using MOCK RCA.")
    except Exception as e:
        logger.warning(f"Bedrock call failed: {e} — using MOCK RCA.")

    return MOCK_RCA, None
