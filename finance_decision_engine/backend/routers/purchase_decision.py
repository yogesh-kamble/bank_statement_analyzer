from fastapi import APIRouter
from backend.tools.purchase_decision.schemas import (
    PurchaseDecisionRequest,
    PurchaseDecisionResponse
)

from backend.tools.purchase_decision.models import (
    PurchaseInput
)

from backend.tools.purchase_decision.analyzer import (
    analyze_purchase
)

from backend.ai.explainer import explain_purchase
from dataclasses import asdict

router = APIRouter(
    prefix="/api/v1/purchase-decision",
    tags=["Purchase Decision"]
)

@router.post(
    "/analyze",
    response_model=PurchaseDecisionResponse
)
def analyze_purchase_decision(
    request: PurchaseDecisionRequest
):

    purchase_input = PurchaseInput(
            monthly_income=request.monthly_income,
            monthly_expenses=request.monthly_expenses,
            current_savings=request.current_savings,

            purchase_amount=request.purchase_amount,

            payment_mode=request.payment_mode,

            down_payment=request.down_payment,

            emi_months=request.emi_months,

            annual_interest_rate=request.annual_interest_rate
    )

    # 1. Engine computes every number and the verdict
    result = analyze_purchase(purchase_input)

    # 2. AI only explains the finished result (never calculates)
    explanation = (
        explain_purchase(purchase_input, result)
        if request.include_ai_explanation
        else None
    )

    return PurchaseDecisionResponse(
        decision=result.decision,

        decision_score=result.decision_score,

        headline=result.headline,

        monthly_emi=result.monthly_emi,

        emergency_runway_months=result.emergency_runway_months,

        savings_remaining=result.savings_remaining,

        recommendation=result.recommendation,

        monthly_surplus_after_emi=result.monthly_surplus_after_emi,

        emi_ratio=result.emi_ratio,

        ai_explanation=asdict(explanation) if explanation else None
    )