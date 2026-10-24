# AI Layer (OpenAI) — explanation only

## Principle
`engine computes -> FACTS json -> AI writes prose -> numbers verified -> response`

* The deterministic engine owns every number and the verdict.
* The AI receives a FACTS object (raw `value` + pre-formatted `display` for each metric) and may only explain.
* After generation, `guardrails.py` rejects any number in the AI text that is not in FACTS. One retry with a corrective note, then a deterministic fallback.
* AI disabled / no key / API error / timeout => `ai_explanation.source = "fallback"` (templated from the same facts). The API never fails because of AI.
* Statement analyzer sends only aggregates and known-merchant names, never raw transaction descriptions.

## Setup
    pip install -r requirements.txt
    cp .env.example .env    # set OPENAI_API_KEY
    uvicorn backend.main:app --reload
    python -m pytest backend/tests -q

## API
* `POST /api/v1/purchase-decision/analyze` — new request flag `include_ai_explanation` (default true); response adds `emi_ratio` and `ai_explanation`.
* `POST /api/v1/statement-analyzer/analyze-statement?explain=true` — response adds `ai_explanation`.

## Layout
    backend/ai/config.py        env settings
    backend/ai/prompts.py       system prompt, task prompts, JSON schema
    backend/ai/explainer.py     OpenAI client wrapper + explain_purchase / explain_statement
    backend/ai/guardrails.py    number-grounding check
    backend/ai/fallbacks.py     deterministic explanations
    backend/ai/formatting.py    INR/percent formatting (done in code, not by AI)
    backend/tools/*/facts.py    FACTS builders
