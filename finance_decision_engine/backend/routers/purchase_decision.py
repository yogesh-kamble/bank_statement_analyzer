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
    "/api/v1/purchase-decision/analyze",
    response_model=PurchaseDecisionResponse
)
def analyze_purchase_decision(
    request: PurchaseDecisionRequest
):
    data = PurchaseInput(
        monthly_income=request.monthly_income,

        monthly_expenses=request.monthly_expenses,

        current_savings=request.current_savings,

        purchase_amount=request.purchase_amount,

        emi_months=request.emi_months,

        annual_interest_rate=request.annual_interest_rate
    )

    result = analyze_purchase(data)

    return PurchaseDecisionResponse(
        monthly_emi=result.monthly_emi,
        savings_after_purchase=result.savings_after_purchase,

        decision_score=result.decision_score,
        emergency_runway_months=result.emergency_runway_months,

        decision=result.decision,
        insight=result.insight,
        recommendation=result.recommendation,
    )