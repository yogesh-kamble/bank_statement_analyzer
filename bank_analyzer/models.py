from dataclasses import dataclass
from typing import List, Dict


@dataclass
class Transaction:
    date: str
    description: str
    amount: float
    balance: float


@dataclass
class CategorizedTransaction:
    transaction: Transaction
    category: str


@dataclass
class AnalysisResult:
    total_spend: float
    category_totals: Dict[str, float]
    top_categories: List[str]
    insight: str = ""
    suggestion: str = ""