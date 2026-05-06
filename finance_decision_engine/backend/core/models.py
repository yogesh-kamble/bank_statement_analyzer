from dataclasses import dataclass
from datetime import datetime


@dataclass
class Transaction:
    date: datetime
    amount: float
    type: str  # "debit" or "credit"
    description: str
