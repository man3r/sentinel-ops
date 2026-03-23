"""
Application configuration via pydantic-settings.
All values are loaded from environment variables or .env file.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────────
    # Format: postgresql+asyncpg://user:password@host:port/dbname
    database_url: str = "postgresql+asyncpg://postgres:localdev@localhost:5432/sentinelops"

    # ── AWS ───────────────────────────────────────────────────────────────────
    aws_region: str = "us-east-1"
    bedrock_model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    bedrock_embed_model_id: str = "amazon.titan-embed-text-v2:0"

    # ── OpenSearch ────────────────────────────────────────────────────────────
    opensearch_endpoint: str = ""
    opensearch_index: str = "sentinelops-incidents"

    # ── Slack ─────────────────────────────────────────────────────────────────
    slack_bot_token: str = ""
    slack_signing_secret: str = ""
    slack_incident_channel: str = "#incidents"

    # ── Perception Engine ─────────────────────────────────────────────────────
    perception_engine_url: str = "http://localhost:8001"

    # ── Agent Behaviour ───────────────────────────────────────────────────────
    min_confidence_threshold: float = 0.75
    reasoning_timeout_seconds: int = 180
    dashboard_url: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
