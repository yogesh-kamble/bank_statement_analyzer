from dataclasses import asdict

from backend.normalizers.registry import get_normalizer
from backend.tools.statement_analyzer.parser import parse_transactions
from backend.tools.statement_analyzer.aggregator import aggregate_transactions
from backend.ai.insight_engine import generate_insight
from backend.ai.explainer import explain_statement


def analyze_statement(file_path: str, bank: str, explain: bool = True):
    # Step 1: Normalize
    normalizer = get_normalizer(bank)
    normalized_data = normalizer(file_path)

    # Step 2: Parse
    transactions = parse_transactions(normalized_data)

    # Step 3: Aggregate (all numbers computed here)
    aggregated = aggregate_transactions(transactions)

    # Step 4: Deterministic insight (kept for backward compatibility)
    insight = generate_insight(aggregated)

    response = {
        **aggregated,

        "insight": {
            "message": insight.insight,
            "suggestion": insight.suggestion
        }
    }

    # Step 5: AI explains the finished numbers (never calculates)
    if explain:
        response["ai_explanation"] = asdict(
            explain_statement(aggregated)
        )

    return response
