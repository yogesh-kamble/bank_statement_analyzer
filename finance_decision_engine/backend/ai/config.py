"""AI layer configuration, read from environment variables.

OPENAI_API_KEY        required to enable AI explanations
OPENAI_MODEL          default: gpt-4o-mini
OPENAI_TEMPERATURE    optional; omitted from the request when unset
                      (some models reject non-default temperatures)
AI_ENABLED            default: true  (set to false to force fallback text)
AI_TIMEOUT_SECONDS    default: 15
AI_MAX_RETRIES        default: 1   (SDK-level retries for network/5xx errors)
"""
import os
from dataclasses import dataclass
from typing import Optional

try:  # optional convenience: load a local .env file if python-dotenv is installed
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class AISettings:
    api_key: Optional[str]
    model: str
    temperature: Optional[float]
    enabled: bool
    timeout_seconds: float
    max_retries: int

    @property
    def is_ready(self) -> bool:
        return self.enabled and bool(self.api_key)


def load_settings() -> AISettings:
    temp = os.getenv("OPENAI_TEMPERATURE", "").strip()
    return AISettings(
        api_key=os.getenv("OPENAI_API_KEY") or None,
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=float(temp) if temp else None,
        enabled=_bool("AI_ENABLED", True),
        timeout_seconds=float(os.getenv("AI_TIMEOUT_SECONDS", "15")),
        max_retries=int(os.getenv("AI_MAX_RETRIES", "1")),
    )
