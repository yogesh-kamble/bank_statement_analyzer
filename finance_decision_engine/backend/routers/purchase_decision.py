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

    result = analyze_purchase(
        PurchaseInput(
            monthly_income=request.monthly_income,
            monthly_expenses=request.monthly_expenses,
            current_savings=request.current_savings,

            purchase_amount=request.purchase_amount,

            payment_mode=request.payment_mode,

            down_payment=request.down_payment,

            emi_months=request.emi_months,

            annual_interest_rate=request.annual_interest_rate
        )
    )

    return PurchaseDecisionResponse(
        decision=result.decision,

        decision_score=result.decision_score,

        headline=result.headline,

        monthly_emi=result.monthly_emi,

        emergency_runway_months=result.emergency_runway_months,

        savings_remaining=result.savings_remaining,

        recommendation=result.recommendation
    )