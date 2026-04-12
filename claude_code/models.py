"""
Data models for ICICI Bank Statement Analyzer.
All models are minimal, immutable-friendly dataclasses.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Transaction:
    """Raw parsed transaction from ICICI CSV."""
    date: str
    description: str
    amount: float          # Negative = expense, Positive = income
    balance: float

    def is_expense(self) -> bool:
        return self.amount < 0


@dataclass
class CategorizedTransaction:
    """Transaction enriched with a spending category."""
    transaction: Transaction
    category: str

    @property
    def amount(self) -> float:
        return self.transaction.amount

    @property
    def description(self) -> str:
        return self.transaction.description


@dataclass
class AnalysisResult:
    """Final output of the analysis pipeline."""
    total_spend: float                          # Always positive
    category_totals: dict[str, float]           # category -> total spend (positive)
    top_categories: list[tuple[str, float]]     # [(category, spend), ...] top 3
    insight: str                                # AI-generated key insight
    suggestion: str                             # AI-generated actionable suggestion
    transaction_count: int                      # Total expense transactions analyzed
