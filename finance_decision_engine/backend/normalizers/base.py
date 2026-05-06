from typing import List, Dict
def normalize(file_path: str) -> List[Dict]:
    """
    Implementations should follow this signature.

    - description: str (lowercased)
    - type: "debit" or "credit"
    - amount: float
    - date: datetime
    Normalize a bank statement file into a list of dicts with keys:
    """
    raise NotImplementedError("Each normalizer should implement normalize(file_path: str) -> List[dict]")

