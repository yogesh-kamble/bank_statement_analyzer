from dataclasses import dataclass


@dataclass
class PurchaseInput:
    monthly_income: float
    monthly_expenses: float
    current_savings: float

    purchase_amount: float

    emi_months: int = 12
    annual_interest_rate: float = 12.0


@dataclass
class PurchaseDecisionResult:
    monthly_emi: float

    emi_ratio: float

    savings_after_purchase: float

    stress_score: int

    decision: str

    insight: str

    recommendation: str