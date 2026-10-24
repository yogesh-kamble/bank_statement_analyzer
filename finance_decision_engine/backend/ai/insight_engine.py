from backend.ai.models import InsightResult


def generate_insight(data: dict) -> InsightResult:
    total_spend = data.get("total_spend", 0)

    # aggregator emits merchant_totals (older callers may pass category_totals)
    category_totals = {
        k: v
        for k, v in (
            data.get("category_totals")
            or data.get("merchant_totals")
            or {}
        ).items()
        if k != "unknown"
    }

    if not category_totals or total_spend <= 0:
        return InsightResult(
            insight="No spending patterns detected.",
            suggestion="Use the app regularly to improve financial insights."
        )

    # Find top category
    top_category = max(
        category_totals,
        key=category_totals.get
    )

    top_amount = category_totals[top_category]

    percentage = (top_amount / total_spend) * 100

    insight = (
        f"{top_category.capitalize()} contributes "
        f"{percentage:.0f}% of your total spending."
    )

    suggestion = (
        f"Try reducing {top_category} expenses by 10-15% "
        f"to improve monthly savings."
    )

    return InsightResult(
        insight=insight,
        suggestion=suggestion
    )