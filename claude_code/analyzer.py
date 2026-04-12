"""
Core analysis pipeline for ICICI Bank Statement Analyzer.

All functions are pure and side-effect free — easy to test in isolation.

Pipeline:
    parse_icici_csv()
        → filter_expenses()
        → categorize_transactions()
        → aggregate_spend()
        → get_top_categories()
        → analyze()  ← orchestrates all of the above
"""

from collections import defaultdict

from categorizer import categorize
from models import AnalysisResult, CategorizedTransaction, Transaction


# ---------------------------------------------------------------------------
# Step 1 — Filter
# ---------------------------------------------------------------------------

def filter_expenses(transactions: list[Transaction]) -> list[Transaction]:
    """
    Return only transactions where money left the account (amount < 0).

    Args:
        transactions: All parsed transactions.

    Returns:
        Subset of transactions that are expenses.
    """
    return [t for t in transactions if t.is_expense()]


# ---------------------------------------------------------------------------
# Step 2 — Categorize
# ---------------------------------------------------------------------------

def categorize_transactions(
    transactions: list[Transaction],
) -> list[CategorizedTransaction]:
    """
    Attach a category to each transaction using keyword rules.

    Args:
        transactions: Expense transactions to categorize.

    Returns:
        List of CategorizedTransaction objects.
    """
    return [
        CategorizedTransaction(transaction=t, category=categorize(t.description))
        for t in transactions
    ]


# ---------------------------------------------------------------------------
# Step 3 — Aggregate
# ---------------------------------------------------------------------------

def aggregate_spend(
    categorized: list[CategorizedTransaction],
) -> dict[str, float]:
    """
    Sum absolute spend amounts per category.

    Args:
        categorized: Categorized expense transactions.

    Returns:
        Dict mapping category → total spend (always positive).
    """
    totals: dict[str, float] = defaultdict(float)
    for ct in categorized:
        totals[ct.category] += abs(ct.amount)   # amounts are negative; abs for readability
    return dict(totals)


# ---------------------------------------------------------------------------
# Step 4 — Rank
# ---------------------------------------------------------------------------

def get_top_categories(
    category_totals: dict[str, float],
    n: int = 3,
) -> list[tuple[str, float]]:
    """
    Return the top N categories by spend, descending.

    Args:
        category_totals: Output of aggregate_spend().
        n: Number of top categories to return (default 3).

    Returns:
        List of (category, total_spend) tuples, highest first.
    """
    sorted_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
    return sorted_categories[:n]


# ---------------------------------------------------------------------------
# Step 5 — Insight prompt template (NO AI called here)
# ---------------------------------------------------------------------------

def build_insight_prompt(
    total_spend: float,
    category_totals: dict[str, float],
    top_categories: list[tuple[str, float]],
) -> str:
    """
    Build a prompt string you can pass to any LLM to generate insights.

    This function is intentionally separated from any AI API call so the
    analyzer stays pure and testable. Plug this prompt into Claude, GPT,
    or any model of your choice.

    Returns:
        A ready-to-send prompt string.
    """
    top_formatted = "\n".join(
        f"  - {cat.title()}: ₹{spend:,.2f}" for cat, spend in top_categories
    )
    all_categories = "\n".join(
        f"  - {cat.title()}: ₹{spend:,.2f}"
        for cat, spend in sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
    )

    return f"""You are a personal finance advisor analyzing an Indian bank statement.

Here is the user's spending summary for the statement period:

Total Spend: ₹{total_spend:,.2f}

Top 3 Spending Categories:
{top_formatted}

All Category Totals:
{all_categories}

Based on this data, provide EXACTLY two things:
1. KEY INSIGHT: One sharp, specific observation about the user's spending pattern.
   - Be specific (mention actual amounts/categories)
   - Do NOT be generic (avoid "you should track your spending")
2. ACTIONABLE SUGGESTION: One concrete step the user can take this month.
   - Must be specific and immediately actionable
   - Tailored to their actual spending profile

Respond in this exact format:
INSIGHT: <your insight here>
SUGGESTION: <your suggestion here>"""


def parse_insight_response(raw_response: str) -> tuple[str, str]:
    """
    Parse the LLM response into (insight, suggestion) strings.

    Args:
        raw_response: Raw text returned by the LLM.

    Returns:
        Tuple of (insight, suggestion). Falls back gracefully if parsing fails.
    """
    insight    = "Unable to generate insight."
    suggestion = "Unable to generate suggestion."

    for line in raw_response.strip().splitlines():
        line = line.strip()
        if line.upper().startswith("INSIGHT:"):
            insight = line[len("INSIGHT:"):].strip()
        elif line.upper().startswith("SUGGESTION:"):
            suggestion = line[len("SUGGESTION:"):].strip()

    return insight, suggestion


# ---------------------------------------------------------------------------
# Orchestrator — analyze()
# ---------------------------------------------------------------------------

def analyze(transactions: list[Transaction]) -> AnalysisResult:
    """
    Run the full analysis pipeline on a list of transactions.

    This function does NOT call any AI — it produces a complete AnalysisResult
    with placeholder insight/suggestion strings. To get AI-generated insights,
    call build_insight_prompt() and send it to your LLM of choice, then use
    parse_insight_response() to update the result.

    Args:
        transactions: Parsed transactions (output of parse_icici_csv).

    Returns:
        AnalysisResult with all computed fields populated.
    """
    expenses            = filter_expenses(transactions)
    categorized         = categorize_transactions(expenses)
    category_totals     = aggregate_spend(categorized)
    top_categories      = get_top_categories(category_totals)
    total_spend         = sum(category_totals.values())

    return AnalysisResult(
        total_spend=round(total_spend, 2),
        category_totals={k: round(v, 2) for k, v in category_totals.items()},
        top_categories=[(cat, round(spend, 2)) for cat, spend in top_categories],
        insight="[Call build_insight_prompt() and send to LLM to populate this]",
        suggestion="[Call build_insight_prompt() and send to LLM to populate this]",
        transaction_count=len(expenses),
    )
