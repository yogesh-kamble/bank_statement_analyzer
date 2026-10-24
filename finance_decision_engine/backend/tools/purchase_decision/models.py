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

    monthly_surplus_after_emi: float

    # Engine-computed figures, exposed so the AI layer never has to derive them
    emi_ratio: float = 0.0              # EMI as % of monthly income
    loan_amount: float = 0.0
    total_repayment: float = 0.0        # EMI x tenure
    total_interest: float = 0.0
    emi_coverage_ratio: float = 0.0     # monthly surplus / EMI (0 for cash)
    monthly_surplus: float = 0.0        # income - expenses, before EMI
