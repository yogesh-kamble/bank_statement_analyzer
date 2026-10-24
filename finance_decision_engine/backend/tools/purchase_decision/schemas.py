# backend/tools/purchase_decision/schemas.py

from pydantic import BaseModel
from typing import List, Literal, Optional


class PurchaseDecisionRequest(BaseModel):
    monthly_income: float
    monthly_expenses: float
    current_savings: float

    purchase_amount: float

    payment_mode: Literal["cash", "emi"]

    down_payment: float = 0

    emi_months: int = 12
    annual_interest_rate: float = 12.0

    # Set false to skip the AI explanation (saves latency/cost)
    include_ai_explanation: bool = True


class AIExplanationSchema(BaseModel):
    summary: str
    key_points: List[str] = []
    risks: List[str] = []
    suggestions: List[str] = []
    source: Literal["ai", "fallback"]
    model: Optional[str] = None


class PurchaseDecisionResponse(BaseModel):
    decision: str

    decision_score: int

    headline: str

    monthly_emi: float

    emergency_runway_months: int

    savings_remaining: float

    recommendation: str

    monthly_surplus_after_emi: float

    emi_ratio: float = 0.0

    ai_explanation: Optional[AIExplanationSchema] = None
