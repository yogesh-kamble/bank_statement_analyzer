from backend.normalizers.registry import get_normalizer
from backend.tools.statement_analyzer.parser import parse_transactions
from backend.tools.statement_analyzer.aggregator import aggregate_transactions
from backend.ai.insight_engine import generate_insight


def analyze_statement(file_path: str, bank: str):
    # Step 1: Normalize
    normalizer = get_normalizer(bank)
    normalized_data = normalizer(file_path)

    # Step 2: Parse
    transactions = parse_transactions(normalized_data)

    # Step 3: Aggregate

    aggregated = aggregate_transactions(transactions)

    insight = generate_insight(aggregated)

    return {
        **aggregated,

        "insight": {
            "message": insight.insight,
            "suggestion": insight.suggestion
        }
    }
