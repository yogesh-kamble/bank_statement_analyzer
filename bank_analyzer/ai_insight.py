from typing import Dict, List, Tuple
import json


def build_insight_prompt(
    total_spend: float,
    category_totals: Dict[str, float],
    top_categories: List[str]
) -> str:
    return f"""
        You are a financial assistant.

        Given:
        - Total Spend: {total_spend}
        - Category Totals: {category_totals}
        - Top Categories: {top_categories}

        Return STRICT JSON:
        {{
        "insight": "...",
        "suggestion": "..."
        }}
    """


def generate_insight(llm_client, prompt: str) -> Tuple[str, str]:
    """
    llm_client: function that takes prompt -> string response
    """

    try:
        raw_response = llm_client(prompt)

        data = json.loads(raw_response)

        return data.get("insight", ""), data.get("suggestion", "")

    except Exception:
        return (
            "Unable to generate insight.",
            "Try reviewing your highest spending category."
        )