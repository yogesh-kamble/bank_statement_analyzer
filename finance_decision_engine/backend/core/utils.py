from datetime import datetime
from typing import Optional

def parse_amount(value: Optional[str]) -> Optional[float]:
    """
    Convert strings like '1,234.56', '(1,234.56)', '' or None to float.
    Returns None when not parseable.
    """
    if value is None:
        return None
    s = str(value).strip()
    if s == "":
        return None
    # remove common thousands separators and whitespace
    s = s.replace(",", "").replace(" ", "")
    # handle parentheses for negative amounts
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
    try:
        return float(s)
    except ValueError:
        return None

def parse_date(value: Optional[str]) -> Optional[datetime]:
    """
    Try a few common date formats. Return datetime or None.
    """
    if value is None:
        return None
    s = str(value).strip()
    if s == "":
        return None
    formats = [
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y-%m-%d",
        "%d-%b-%Y",
        "%d %b %Y",
        "%d %B %Y",
        "%Y/%m/%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    # Try ISO parse as last resort
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None
