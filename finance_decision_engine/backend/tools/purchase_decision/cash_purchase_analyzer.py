from .models import PurchaseInput, PurchaseDecisionResult

def analyze_cash_purchase(
    data: PurchaseInput
):

    savings_remaining = (
        data.current_savings -
        data.purchase_amount
    )

    runway = int(
        savings_remaining /
        data.monthly_expenses
    )

    if runway >= 12:
        decision = "SAFE"
        score = 90
    elif runway >= 6:
        decision = "MODERATE"
        score = 65
    else:
        decision = "RISKY"
        score = 30

    return PurchaseDecisionResult(
        decision=decision,
        decision_score=score,

        headline=f"You will retain {runway} months of emergency fund.",

        monthly_emi=0,

        emergency_runway_months=runway,

        savings_remaining=savings_remaining,

        recommendation="Maintain at least 6 months emergency fund."
    )