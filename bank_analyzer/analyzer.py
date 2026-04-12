from typing import List, Optional, Callable

from models import Transaction, AnalysisResult
from categorizer import categorize_transactions
from ai_insight import build_insight_prompt, generate_insight

from collections import defaultdict


def filter_expenses(transactions: List[Transaction]) -> List[Transaction]:
    return [txn for txn in transactions if txn.amount < 0]


def aggregate_spend(categorized_txns):
    totals = defaultdict(float)

    for ctxn in categorized_txns:
        totals[ctxn.category] += abs(ctxn.transaction.amount)

    return dict(totals)


def get_top_categories(category_totals, n=3):
    sorted_categories = sorted(
        category_totals.items(),
        key=lambda x: x[1],
        reverse=True
    )
    return [cat for cat, _ in sorted_categories[:n]]


def analyze(
    transactions: List[Transaction],
    llm_client: Optional[Callable[[str], str]] = None
) -> AnalysisResult:

    expenses = filter_expenses(transactions)

    categorized = categorize_transactions(expenses)

    category_totals = aggregate_spend(categorized)

    total_spend = sum(category_totals.values())

    top_categories = get_top_categories(category_totals)

    insight = ""
    suggestion = ""

    # 🔥 AI integration (optional)
    if llm_client:
        prompt = build_insight_prompt(
            total_spend,
            category_totals,
            top_categories
        )

        insight, suggestion = generate_insight(llm_client, prompt)

    return AnalysisResult(
        total_spend=total_spend,
        category_totals=category_totals,
        top_categories=top_categories,
        insight=insight,
        suggestion=suggestion
    )