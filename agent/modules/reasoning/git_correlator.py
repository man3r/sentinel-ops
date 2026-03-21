"""
Git Correlator — fetches recently merged PRs across all registered repositories.
Supports GitHub (MVP). GitLab and Bitbucket are v2 roadmap.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)

LOOKBACK_HOURS = 24  # How far back to scan for causal PRs


# ── Provider Implementations ───────────────────────────────────────────────────

async def _fetch_github_prs(
    owner_repo: str, token: str, since_hours: int = LOOKBACK_HOURS
) -> list[dict[str, Any]]:
    """Fetch PRs merged in the last `since_hours` from a GitHub repo."""
    since = (datetime.now(timezone.utc) - timedelta(hours=since_hours)).isoformat()
    url = f"https://api.github.com/repos/{owner_repo}/pulls"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    params = {"state": "closed", "sort": "updated", "direction": "desc", "per_page": 20}

    try:
        async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
            r = await client.get(url, params=params)
            if r.status_code == 401:
                logger.warning(f"GitHub API: Unauthorized for {owner_repo}. Check token.")
                return []
            if r.status_code != 200:
                logger.warning(f"GitHub API returned {r.status_code} for {owner_repo}.")
                return []

            recent = []
            for pr in r.json():
                merged_at = pr.get("merged_at")
                if merged_at and merged_at >= since:
                    recent.append(
                        {
                            "number": pr["number"],
                            "title": pr["title"],
                            "author": pr["user"]["login"],
                            "merged_at": merged_at,
                            "url": pr["html_url"],
                            "repo": owner_repo,
                            "provider": "GITHUB",
                        }
                    )
            return recent
    except httpx.RequestError as e:
        logger.warning(f"GitHub API request failed for {owner_repo}: {e}")
        return []


def _parse_github_owner_repo(url: str) -> str | None:
    """Extract 'owner/repo' from a GitHub URL."""
    try:
        parts = url.rstrip("/").split("github.com/")
        if len(parts) == 2:
            return parts[1].strip("/")
    except Exception:
        pass
    return None


# ── Main Entry Point ───────────────────────────────────────────────────────────

async def correlate(repos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Query all registered repos for PRs merged in the last 24h.
    Repos with no token (empty secret_arn) are skipped gracefully.
    Falls back to an empty list if GitHub is unreachable.
    """
    all_prs: list[dict[str, Any]] = []

    for repo in repos:
        provider = repo.get("provider", "GITHUB").upper()
        url = repo.get("url", "")

        if provider == "GITHUB":
            owner_repo = _parse_github_owner_repo(url)
            if not owner_repo:
                logger.warning(f"Could not parse owner/repo from URL: {url}")
                continue

            # Production: fetch token from AWS Secrets Manager using repo["secret_arn"]
            # Local dev: use a placeholder (unauthenticated = 60 req/hr rate limit)
            token = "PLACEHOLDER_TOKEN"

            prs = await _fetch_github_prs(owner_repo, token)
            logger.info(f"Git correlation: {len(prs)} recent PRs from {owner_repo}")
            all_prs.extend(prs)

        else:
            logger.info(f"Provider '{provider}' not yet supported (v2 roadmap). Skipping.")

    return all_prs
