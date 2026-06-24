# backend/tools/purchase_decision/models.py

from dataclasses import dataclass


@dataclass
class PurchaseInput:
    monthly_income: float
    monthly_expenses: float
    current_savings: float

    purchase_amount: float

    payment_mode: str

    down_payment: float = 0

    emi_months: int = 12
    annual_interest_rate: float = 12.0


@dataclass
class PurchaseDecisionResult:
    decision: str

    decision_score: int

    headline: str

    monthly_emi: float

    emergency_runway_months: int

    savings_remaining: float

    recommendation: str