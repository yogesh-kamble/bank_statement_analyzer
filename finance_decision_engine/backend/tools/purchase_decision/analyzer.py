from backend.tools.purchase_decision.models import (
    PurchaseInput,
    PurchaseDecisionResult
)

from backend.tools.purchase_decision.calculator import (
    calculate_emi
)

from backend.tools.purchase_decision.rules import (
    calculate_stress_score
)

from backend.tools.purchase_decision.insight import (
    generate_purchase_insight
)


# def analyze_purchase(
#     data: PurchaseInput
# ) -> PurchaseDecisionResult:
#
#     emi = calculate_emi(
#         principal=data.purchase_amount,
#         annual_interest_rate=data.annual_interest_rate,
#         months=data.emi_months
#     )
#
#     stress_score, decision = calculate_stress_score(
#         monthly_income=data.monthly_income,
#         monthly_expenses=data.monthly_expenses,
#         monthly_emi=emi,
#         current_savings=data.current_savings,
#         purchase_amount=data.purchase_amount
#     )
#
#     insight, recommendation = generate_purchase_insight(
#         decision=decision,
#         stress_score=stress_score
#     )
#
#     decision_score = max(0, 100 - stress_score)
#
#     emergency_runway_months = 0
#     savings_after_purchase = (
#             data.current_savings - data.purchase_amount
#     )
#     if data.monthly_expenses > 0:
#         emergency_runway_months = int(
#             savings_after_purchase / data.monthly_expenses
#         )
#
#     return PurchaseDecisionResult(
#         monthly_emi=emi,
#         savings_after_purchase=savings_after_purchase,
#
#         stress_score=stress_score,
#         decision_score=decision_score,
#         emergency_runway_months=emergency_runway_months,
#
#         decision=decision,
#         insight=insight,
#         recommendation=recommendation,
#     )
# backend/tools/purchase_decision/analyzer.py

from .models import (
    PurchaseInput,
    PurchaseDecisionResult
)

from .cash_purchase_analyzer import analyze_cash_purchase
from .emi_purchase_analyzer import analyze_emi_purchase

def analyze_purchase(
    data: PurchaseInput
) -> PurchaseDecisionResult:

    if data.payment_mode == "cash":
        return analyze_cash_purchase(data)

    return analyze_emi_purchase(data)