"""
ICICI Bank CSV parser.

ICICI exports statements with columns similar to:
    Date | Description | Debit | Credit | Balance

Notes:
- Debit   = money going out (expense)  → stored as negative amount
- Credit  = money coming in (income)   → stored as positive amount
- Some rows may have empty Debit or Credit cells (not both)
- Header row detection is flexible (case-insensitive column matching)
"""

import csv
import logging
from pathlib import Path

from models import Transaction

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Column name aliases — handles slight variations in ICICI CSV exports
# ---------------------------------------------------------------------------
_DATE_ALIASES        = {"date", "transaction date", "txn date", "value date"}
_DESCRIPTION_ALIASES = {"particulars", "description", "narration", "remarks", "txn remarks"}
_DEBIT_ALIASES       = {"withdrawals", "withdrawal", "debit", "withdrawal amt", "debit amount"}
_CREDIT_ALIASES      = {"deposits", "deposit", "credit", "deposit amt", "credit amount"}
_BALANCE_ALIASES     = {"balance", "closing balance", "available balance"}


def _match_column(header: str, aliases: set[str]) -> bool:
    return header.strip().lower() in aliases


def _find_column_index(headers: list[str], aliases: set[str]) -> int | None:
    """Return index of the first header that matches any alias, or None."""
    for i, h in enumerate(headers):
        if _match_column(h, aliases):
            return i
    return None


def _parse_amount(value: str) -> float:
    """
    Parse a currency string to float.

    Handles:
    - Empty strings → 0.0
    - Comma-separated numbers: "1,23,456.78" → 123456.78
    - Values with ₹ or Rs prefix
    """
    if not value or not value.strip():
        return 0.0
    cleaned = (
        value.strip()
        .replace(",", "")
        .replace("₹", "")
        .replace("Rs.", "")
        .replace("Rs", "")
        .strip()
    )
    try:
        return float(cleaned)
    except ValueError:
        logger.warning("Could not parse amount: %r — defaulting to 0.0", value)
        return 0.0


def normalize_amount(debit: str, credit: str) -> float:
    """
    Convert raw debit/credit strings into a single signed float.

    - Debit  → negative (money out)
    - Credit → positive (money in)
    - If both are non-zero (shouldn't happen), debit takes precedence.

    Args:
        debit:  Raw debit cell value from CSV.
        credit: Raw credit cell value from CSV.

    Returns:
        Signed float representing the transaction amount.
    """
    debit_val  = _parse_amount(debit)
    credit_val = _parse_amount(credit)

    if debit_val > 0:
        return -debit_val       # expense
    if credit_val > 0:
        return credit_val       # income
    return 0.0                  # neither (e.g. opening balance row)


def _skip_row(row: list[str]) -> bool:
    """Return True for rows that should be ignored (blank, summary rows, etc.)."""
    stripped = [cell.strip() for cell in row]
    # Skip completely empty rows
    if not any(stripped):
        return True
    # Skip ICICI summary rows that start with keywords
    first = stripped[0].lower()
    skip_prefixes = ("opening balance", "closing balance", "total", "sr.", "statement")
    return any(first.startswith(p) for p in skip_prefixes)


def parse_icici_csv(file_path: str | Path) -> list[Transaction]:
    """
    Parse an ICICI Bank CSV statement into a list of Transaction objects.

    Args:
        file_path: Path to the ICICI CSV file.

    Returns:
        List of Transaction objects. Empty list if file has no valid rows.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If required columns (Date, Description, Debit/Credit) are missing.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    transactions: list[Transaction] = []

    with open(path, newline="", encoding="utf-8-sig") as csvfile:
        # Use csv.reader for robustness with quoted fields
        reader = csv.reader(csvfile)

        headers: list[str] | None = None
        date_idx = desc_idx = debit_idx = credit_idx = balance_idx = None

        for line_num, row in enumerate(reader, start=1):
            # ── Detect header row ────────────────────────────────────────
            if headers is None:
                if any(_match_column(cell, _DATE_ALIASES) for cell in row):
                    headers = row
                    date_idx    = _find_column_index(headers, _DATE_ALIASES)
                    desc_idx    = _find_column_index(headers, _DESCRIPTION_ALIASES)
                    debit_idx   = _find_column_index(headers, _DEBIT_ALIASES)
                    credit_idx  = _find_column_index(headers, _CREDIT_ALIASES)
                    balance_idx = _find_column_index(headers, _BALANCE_ALIASES)

                    missing = []
                    if date_idx is None:    missing.append("Date")
                    if desc_idx is None:    missing.append("Description")
                    if debit_idx is None and credit_idx is None:
                        missing.append("Debit or Credit")

                    if missing:
                        raise ValueError(
                            f"CSV is missing required columns: {', '.join(missing)}. "
                            f"Found headers: {headers}"
                        )
                continue  # Header row itself is not a transaction

            # ── Skip non-data rows ───────────────────────────────────────
            if _skip_row(row):
                continue

            # ── Safely extract cells ─────────────────────────────────────
            def _get(idx: int | None) -> str:
                if idx is None or idx >= len(row):
                    return ""
                return row[idx].strip()

            date        = _get(date_idx)
            description = _get(desc_idx)
            debit_raw   = _get(debit_idx)
            credit_raw  = _get(credit_idx)
            balance_raw = _get(balance_idx)

            # Skip rows missing both date and description (malformed)
            if not date and not description:
                logger.debug("Line %d: skipping row with no date/description", line_num)
                continue

            amount  = normalize_amount(debit_raw, credit_raw)
            balance = _parse_amount(balance_raw)

            transactions.append(Transaction(
                date=date,
                description=description,
                amount=amount,
                balance=balance,
            ))

    if headers is None:
        raise ValueError(
            "Could not detect a valid ICICI CSV header row. "
            "Expected columns: Date, Description, Debit/Credit, Balance."
        )

    logger.info("Parsed %d transactions from %s", len(transactions), path.name)
    return transactions
