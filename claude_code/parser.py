"""
ICICI Bank CSV parser.

Supports two ICICI export formats, auto-detected from headers:

FORMAT A — Savings / Current account statement:
    DATE | MODE | PARTICULARS | DEPOSITS | WITHDRAWALS | BALANCE
    - Two separate columns for money in (DEPOSITS) and money out (WITHDRAWALS)

FORMAT B — Credit card statement:
    Date | Sr.No. | Transaction Details | Reward Point Header |
    Intl.Amount | Amount(in Rs) | BillingAmountSign
    - Single amount column (Amount(in Rs)) + sign column (BillingAmountSign)
    - BillingAmountSign: "Dr" = debit/expense, "Cr" = credit/refund

Notes:
- Both formats produce the same Transaction objects downstream.
- Header detection is case-insensitive and alias-based.
- The format is detected automatically — no user input required.
"""

import csv
import logging
from enum import Enum, auto
from pathlib import Path

from models import Transaction

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Detected format enum
# ---------------------------------------------------------------------------

class _Format(Enum):
    ACCOUNT    = auto()   # FORMAT A: separate DEPOSITS / WITHDRAWALS columns
    CREDITCARD = auto()   # FORMAT B: Amount(in Rs) + BillingAmountSign


# ---------------------------------------------------------------------------
# Column name aliases
# ---------------------------------------------------------------------------

# Shared
_DATE_ALIASES = {"date", "transaction date", "txn date", "value date"}

# Format A
_DESCRIPTION_ALIASES = {"particulars", "description", "narration", "remarks", "txn remarks"}
_DEBIT_ALIASES       = {"withdrawals", "withdrawal", "debit", "withdrawal amt", "debit amount"}
_CREDIT_ALIASES      = {"deposits", "deposit", "credit", "deposit amt", "credit amount"}
_BALANCE_ALIASES     = {"balance", "closing balance", "available balance"}

# Format B (credit card)
_CC_DESCRIPTION_ALIASES = {"transaction details", "transaction description", "particulars"}
_CC_AMOUNT_ALIASES      = {"amount(in rs)", "amount(in rs.)", "billing amount", "amount"}
_CC_SIGN_ALIASES        = {"billingamountsign", "billing amount sign", "dr/cr", "type"}


def _match_column(header: str, aliases: set[str]) -> bool:
    return header.strip().lower() in aliases


def _find_column_index(headers: list[str], aliases: set[str]) -> int | None:
    """Return index of the first header that matches any alias, or None."""
    for i, h in enumerate(headers):
        if _match_column(h, aliases):
            return i
    return None


def _detect_format(headers: list[str]) -> _Format:
    """
    Inspect header names and return which CSV format this file uses.

    Credit card format is identified by the presence of BillingAmountSign
    or Amount(in Rs) columns. Falls back to ACCOUNT format.
    """
    lowered = {h.strip().lower() for h in headers}
    cc_markers = _CC_SIGN_ALIASES | _CC_AMOUNT_ALIASES
    if lowered & cc_markers:        # non-empty intersection
        return _Format.CREDITCARD
    return _Format.ACCOUNT


# ---------------------------------------------------------------------------
# Amount parsing
# ---------------------------------------------------------------------------

def _parse_amount(value: str) -> float:
    """
    Parse a currency string to float.

    Handles:
    - Empty strings       → 0.0
    - Indian comma format → "1,23,456.78" → 123456.78
    - Currency prefixes   → ₹, Rs., Rs
    - Invalid strings     → 0.0 with a warning log
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
    Format A: Convert separate debit/credit strings into a single signed float.

    - Debit (WITHDRAWALS) → negative  (money out)
    - Credit (DEPOSITS)   → positive  (money in)
    - If both non-zero (shouldn't happen), debit takes precedence.
    """
    debit_val  = _parse_amount(debit)
    credit_val = _parse_amount(credit)

    if debit_val > 0:
        return -debit_val
    if credit_val > 0:
        return credit_val
    return 0.0


def normalize_amount_with_sign(amount: str, sign: str) -> float:
    """
    Format B: Convert a single amount + BillingAmountSign into a signed float.

    BillingAmountSign values:
    - "Dr" (Debit)  → negative (expense / charge on card)
    - "Cr" (Credit) → positive (payment / refund to card)

    Args:
        amount: Raw value from Amount(in Rs) column.
        sign:   Raw value from BillingAmountSign column ("Dr" or "Cr").

    Returns:
        Signed float. Unknown sign tokens are treated as debits (safe default).
    """
    value = _parse_amount(amount)
    if value == 0.0:
        return 0.0

    sign_normalized = sign.strip().lower()
    if sign_normalized == "cr":
        return value    # credit/refund → positive
    # "dr", empty, or anything else → treat as debit (expense)
    return -value


# ---------------------------------------------------------------------------
# Row filter
# ---------------------------------------------------------------------------

def _skip_row(row: list[str]) -> bool:
    """Return True for rows that should not produce a Transaction."""
    stripped = [cell.strip() for cell in row]
    if not any(stripped):
        return True
    first = stripped[0].lower()
    skip_prefixes = ("opening balance", "closing balance", "total", "statement")
    return any(first.startswith(p) for p in skip_prefixes)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_icici_csv(file_path: str | Path) -> list[Transaction]:
    """
    Parse an ICICI Bank CSV statement into a list of Transaction objects.

    Auto-detects between:
    - Format A: savings/current account (DEPOSITS / WITHDRAWALS columns)
    - Format B: credit card statement   (Amount(in Rs) + BillingAmountSign columns)

    Args:
        file_path: Path to the ICICI CSV file.

    Returns:
        List of Transaction objects (may be empty if no valid data rows).

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the header row is missing or required columns are absent.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    transactions: list[Transaction] = []

    with open(path, newline="", encoding="utf-8-sig") as csvfile:
        reader = csv.reader(csvfile)

        fmt: _Format | None = None
        headers: list[str] | None = None

        # Format A indices
        date_idx = desc_idx = debit_idx = credit_idx = balance_idx = None
        # Format B indices
        cc_date_idx = cc_desc_idx = cc_amount_idx = cc_sign_idx = None

        for line_num, row in enumerate(reader, start=1):

            # ── Detect header row ─────────────────────────────────────────
            if headers is None:
                if not any(_match_column(cell, _DATE_ALIASES) for cell in row):
                    continue    # not a header row yet — skip preamble lines

                headers = row
                fmt     = _detect_format(headers)
                logger.info("Detected format: %s", fmt.name)

                if fmt is _Format.ACCOUNT:
                    date_idx    = _find_column_index(headers, _DATE_ALIASES)
                    desc_idx    = _find_column_index(headers, _DESCRIPTION_ALIASES)
                    debit_idx   = _find_column_index(headers, _DEBIT_ALIASES)
                    credit_idx  = _find_column_index(headers, _CREDIT_ALIASES)
                    balance_idx = _find_column_index(headers, _BALANCE_ALIASES)

                    missing = []
                    if date_idx is None:  missing.append("Date")
                    if desc_idx is None:  missing.append("Particulars/Description")
                    if debit_idx is None and credit_idx is None:
                        missing.append("Deposits or Withdrawals")
                    if missing:
                        raise ValueError(
                            f"Format A CSV missing required columns: {', '.join(missing)}. "
                            f"Found: {headers}"
                        )

                else:  # CREDITCARD
                    cc_date_idx   = _find_column_index(headers, _DATE_ALIASES)
                    cc_desc_idx   = _find_column_index(headers, _CC_DESCRIPTION_ALIASES)
                    cc_amount_idx = _find_column_index(headers, _CC_AMOUNT_ALIASES)
                    cc_sign_idx   = _find_column_index(headers, _CC_SIGN_ALIASES)

                    missing = []
                    if cc_date_idx is None:   missing.append("Date")
                    if cc_desc_idx is None:   missing.append("Transaction Details")
                    if cc_amount_idx is None: missing.append("Amount(in Rs)")
                    if cc_sign_idx is None:   missing.append("BillingAmountSign")
                    if missing:
                        raise ValueError(
                            f"Format B (credit card) CSV missing required columns: "
                            f"{', '.join(missing)}. Found: {headers}"
                        )

                continue    # header row is never a transaction

            # ── Skip non-data rows ────────────────────────────────────────
            if _skip_row(row):
                continue

            # ── Safe cell extractor ───────────────────────────────────────
            def _get(idx: int | None) -> str:
                if idx is None or idx >= len(row):
                    return ""
                return row[idx].strip()

            # ── Build Transaction based on detected format ─────────────────
            if fmt is _Format.ACCOUNT:
                date        = _get(date_idx)
                description = _get(desc_idx)

                if not date and not description:
                    logger.debug("Line %d: skipping — no date/description", line_num)
                    continue

                amount  = normalize_amount(_get(debit_idx), _get(credit_idx))
                balance = _parse_amount(_get(balance_idx))

            else:  # CREDITCARD
                date        = _get(cc_date_idx)
                description = _get(cc_desc_idx)

                if not date and not description:
                    logger.debug("Line %d: skipping — no date/description", line_num)
                    continue

                amount  = normalize_amount_with_sign(_get(cc_amount_idx), _get(cc_sign_idx))
                balance = 0.0   # credit card statements don't carry a running balance

            transactions.append(Transaction(
                date=date,
                description=description,
                amount=amount,
                balance=balance,
            ))

    if headers is None:
        raise ValueError(
            "Could not detect a valid ICICI CSV header row. "
            "Expected a row containing a 'Date' column."
        )

    logger.info("Parsed %d transactions from %s", len(transactions), path.name)
    return transactions
