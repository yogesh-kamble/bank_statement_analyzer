from .models import PurchaseInput, PurchaseDecisionResult
from .emi import calculate_emi

def analyze_emi_purchase(
    data: PurchaseInput
):

    loan_amount = (
        data.purchase_amount -
        data.down_payment
    )

    emi = calculate_emi(
        principal=loan_amount,
        annual_interest_rate=data.annual_interest_rate,
        months=data.emi_months
    )

    monthly_surplus = (
        data.monthly_income -
        data.monthly_expenses
    )

    coverage_ratio = (
        monthly_surplus / emi
    )

    savings_remaining = (
        data.current_savings -
        data.down_payment
    )

    runway = int(
        savings_remaining /
        data.monthly_expenses
    )

    if coverage_ratio > 1.5:
        decision = "SAFE"
        score = 90

    elif coverage_ratio > 1:
        decision = "MODERATE"
        score = 65

    else:
        decision = "RISKY"
        score = 35

    return PurchaseDecisionResult(
        decision=decision,
        decision_score=score,

        headline=(
            f"Your EMI uses "
            f"{round((emi / data.monthly_income) * 100)}%"
            f" of income."
        ),

        monthly_emi=round(emi, 2),

        emergency_runway_months=runway,

        savings_remaining=savings_remaining,

        recommendation=(
            "Ensure EMI can be paid from monthly surplus."
        )
    )