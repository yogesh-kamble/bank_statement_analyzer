from .models import PurchaseInput, PurchaseDecisionResult
from .emi import calculate_emi


def analyze_emi_purchase(
    data: PurchaseInput
):

    # -----------------------------------------
    # 1. Calculate loan amount
    # -----------------------------------------

    loan_amount = (
        data.purchase_amount -
        data.down_payment
    )

    # -----------------------------------------
    # 2. Calculate EMI
    # -----------------------------------------

    emi = calculate_emi(
        principal=loan_amount,
        annual_interest_rate=data.annual_interest_rate,
        months=data.emi_months
    )

    # -----------------------------------------
    # 3. Current monthly surplus
    # -----------------------------------------

    monthly_surplus = (
        data.monthly_income -
        data.monthly_expenses
    )

    # -----------------------------------------
    # 4. Monthly surplus after new EMI
    # -----------------------------------------

    monthly_surplus_after_emi = (
        monthly_surplus -
        emi
    )

    # -----------------------------------------
    # 5. EMI coverage ratio
    # -----------------------------------------

    if emi > 0:

        coverage_ratio = (
            monthly_surplus / emi
        )

    else:

        coverage_ratio = float("inf")

    # -----------------------------------------
    # 6. Savings after down payment
    # -----------------------------------------

    savings_remaining = (
        data.current_savings -
        data.down_payment
    )

    # -----------------------------------------
    # 7. Post-purchase monthly burn
    # -----------------------------------------

    post_purchase_monthly_burn = (
        data.monthly_expenses +
        emi
    )

    # -----------------------------------------
    # 8. Emergency runway
    # -----------------------------------------

    if post_purchase_monthly_burn > 0:

        runway = int(
            savings_remaining /
            post_purchase_monthly_burn
        )

    else:

        runway = 0

    # -----------------------------------------
    # 9. Decision
    # -----------------------------------------

    if (
        coverage_ratio > 1.5
        and runway >= 6
        and monthly_surplus_after_emi > 0
    ):

        decision = "SAFE"
        score = 90

    elif (
        coverage_ratio > 1
        and runway >= 3
        and monthly_surplus_after_emi > 0
    ):

        decision = "MODERATE"
        score = 65

    else:

        decision = "RISKY"
        score = 35

    # -----------------------------------------
    # 10. Result
    # -----------------------------------------

    return PurchaseDecisionResult(

        decision=decision,

        decision_score=score,

        headline=(
            f"Your EMI uses "
            f"{round((emi / data.monthly_income) * 100)}% "
            f"of your monthly income."
        ),

        monthly_emi=round(
            emi,
            2
        ),

        emergency_runway_months=runway,

        savings_remaining=round(
            savings_remaining,
            2
        ),

        recommendation=(
            "Ensure the new EMI can be comfortably "
            "paid from your existing monthly surplus "
            "while maintaining an adequate emergency fund."
        )
    )