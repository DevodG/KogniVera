"""
Central configuration. Every external API key / toggle lives here and is read
from environment variables (see /.env.example at the repo root).

Nothing in this file should ever contain a real secret — only names and defaults.
"""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env relative to this file, not the process CWD.
# Keeps the app runnable from any directory (repo root, backend/, etc.).
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---------------------------------------------------------------
    # LLM — NVIDIA NIM (OpenAI-compatible endpoint)
    # ---------------------------------------------------------------
    NVIDIA_API_KEY: str = ""
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    # Primary reasoning/tool-calling model.
    # Default: meta/llama-3.1-70b-instruct — widely available on NIM free tier.
    # Swap freely — every model on build.nvidia.com speaks the same OpenAI-style API.
    AGENT_MODEL: str = "meta/llama-3.1-70b-instruct"
    # Cheaper/faster model for low-stakes routing or summarization calls.
    FAST_MODEL: str = "meta/llama-3.1-8b-instruct"

    # ---------------------------------------------------------------
    # Optional: swap NIM for a different provider without touching agent code.
    # If OPENAI_API_KEY / ANTHROPIC_API_KEY are set and LLM_PROVIDER is
    # changed, app/agent/llm_client.py will route there instead.
    # ---------------------------------------------------------------
    LLM_PROVIDER: str = "nvidia_nim"  # one of: nvidia_nim | openai | anthropic
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # ---------------------------------------------------------------
    # Real travel data (all optional — mock data is used until these are set)
    # ---------------------------------------------------------------
    AMADEUS_CLIENT_ID: str = ""
    AMADEUS_CLIENT_SECRET: str = ""
    AMADEUS_ENV: str = "test"  # "test" (free sandbox) or "production"

    SKYSCANNER_API_KEY: str = ""          # flights (RapidAPI listing)
    HOTELBEDS_API_KEY: str = ""           # hotels
    HOTELBEDS_API_SECRET: str = ""
    GOOGLE_PLACES_API_KEY: str = ""       # nearby activities / points of interest
    EXCHANGE_RATE_API_KEY: str = ""       # live currency conversion

    # ---------------------------------------------------------------
    # Notifications (used by the proactive-monitoring agent, Week 4 feature)
    # ---------------------------------------------------------------
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""
    RESEND_API_KEY: str = ""              # transactional email (plan summaries, alerts)

    # ---------------------------------------------------------------
    # Budget guardrail
    # ---------------------------------------------------------------
    DEFAULT_SESSION_SPEND_CAP_USD: float = 25000  # interpreted in the trip's stated currency
    AGENT_BUDGET_HARD_STOP: bool = True

    # ---------------------------------------------------------------
    # Persistence
    # ---------------------------------------------------------------
    DATABASE_URL: str = "sqlite+aiosqlite:///./concierge.db"

    # ---------------------------------------------------------------
    # App
    # ---------------------------------------------------------------
    APP_ENV: str = "development"
    CORS_ORIGINS: str = "http://localhost:5173"


settings = Settings()
