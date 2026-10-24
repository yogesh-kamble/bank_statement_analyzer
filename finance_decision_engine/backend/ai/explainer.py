"""OpenAI-backed explanation service.

The AI receives finished, engine-computed FACTS and returns prose only.
On any failure (no key, API error, bad JSON, numbers not grounded in FACTS)
the caller's deterministic fallback explanation is returned instead.
"""
import json
import logging
from functools import lru_cache
from typing import Any, Dict, Optional

from backend.ai import prompts
from backend.ai.config import AISettings, load_settings
from backend.ai.guardrails import find_unsupported_numbers
from backend.ai.models import Explanation

logger = logging.getLogger(__name__)


class OpenAIExplainer:
    def __init__(self, settings: Optional[AISettings] = None, client: Any = None):
        self.settings = settings or load_settings()
        self._client = client  # injectable for tests

    @property
    def available(self) -> bool:
        return self._client is not None or self.settings.is_ready

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI  # imported lazily so the app runs without the SDK

            self._client = OpenAI(
                api_key=self.settings.api_key,
                timeout=self.settings.timeout_seconds,
                max_retries=self.settings.max_retries,
            )
        return self._client

    def _call(self, task: str, facts: Dict[str, Any], retry_note: Optional[str]) -> Explanation:
        user_content = f"{task}\n\nFACTS:\n{json.dumps(facts, ensure_ascii=False, indent=2)}"
        messages = [
            {"role": "system", "content": prompts.SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]
        if retry_note:
            messages.append({"role": "user", "content": retry_note})

        kwargs: Dict[str, Any] = {
            "model": self.settings.model,
            "messages": messages,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "finance_explanation",
                    "strict": True,
                    "schema": prompts.RESPONSE_SCHEMA,
                },
            },
        }
        if self.settings.temperature is not None:
            kwargs["temperature"] = self.settings.temperature

        resp = self._get_client().chat.completions.create(**kwargs)
        data = json.loads(resp.choices[0].message.content)
        return Explanation(
            summary=str(data["summary"]).strip(),
            key_points=[str(x).strip() for x in data.get("key_points", [])],
            risks=[str(x).strip() for x in data.get("risks", [])],
            suggestions=[str(x).strip() for x in data.get("suggestions", [])],
            source="ai",
            model=self.settings.model,
        )

    def explain(self, task: str, facts: Dict[str, Any], fallback: Explanation) -> Explanation:
        if not self.available:
            return fallback

        retry_note = None
        for attempt in (1, 2):
            try:
                result = self._call(task, facts, retry_note)
            except Exception as exc:  # network, auth, rate limit, bad JSON ...
                logger.warning("AI explanation failed (%s): %s", type(exc).__name__, exc)
                return fallback

            unsupported = find_unsupported_numbers(result, facts)
            if not unsupported:
                return result

            logger.warning("AI output rejected, ungrounded numbers: %s", unsupported)
            retry_note = prompts.RETRY_NOTE.format(numbers=", ".join(str(n) for n in unsupported))

        return fallback


@lru_cache(maxsize=1)
def get_explainer() -> OpenAIExplainer:
    return OpenAIExplainer()


# ---- tool-level entry points -------------------------------------------------
def explain_purchase(data, result, explainer: Optional[OpenAIExplainer] = None) -> Explanation:
    from backend.ai.fallbacks import purchase_fallback
    from backend.tools.purchase_decision.facts import build_purchase_facts

    facts = build_purchase_facts(data, result)
    return (explainer or get_explainer()).explain(
        prompts.PURCHASE_TASK, facts, purchase_fallback(facts)
    )


def explain_statement(aggregated: Dict[str, Any], explainer: Optional[OpenAIExplainer] = None) -> Explanation:
    from backend.ai.fallbacks import statement_fallback
    from backend.tools.statement_analyzer.facts import build_statement_facts

    facts = build_statement_facts(aggregated)
    return (explainer or get_explainer()).explain(
        prompts.STATEMENT_TASK, facts, statement_fallback(facts)
    )
