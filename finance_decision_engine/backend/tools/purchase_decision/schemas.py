from pydantic import BaseModel


class PurchaseDecisionRequest(BaseModel):
    monthly_income: float

    monthly_expenses: float

    current_savings: float

    purchase_amount: float

    emi_months: int = 12

    annual_interest_rate: float = 12.0


class PurchaseDecisionResponse(BaseModel):

    monthly_emi: float

    savings_after_purchase: float

    decision_score: int

    emergency_runway_months: int

    decision: str

    insight: str

    recommendation: str