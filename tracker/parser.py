"""
Transaction parser.
Extracts amount, type (debit/credit), merchant, and date from bank email text.
Uses regex pattern matching — no AI/ML needed.
"""
import re
from datetime import datetime
from email.utils import parsedate_to_datetime


# --- Amount patterns ---
# Matches: Rs 1,500.00 | INR 2500 | Rs.500 | ₹1500
AMOUNT_RE = re.compile(
    r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE
)

# --- Debit keywords ---
DEBIT_KEYWORDS = [
    "debited", "debit", "spent", "withdrawn", "purchase",
    "paid", "payment of", "charged", "sent to",
]

# --- Credit keywords ---
CREDIT_KEYWORDS = [
    "credited", "credit", "received", "refund", "cashback",
    "deposited", "reversed",
]

# --- Merchant patterns ---
# Matches text after: at, to, towards, VPA, UPI — stops at date/noise words
MERCHANT_RE = re.compile(
    r"(?:at|to|towards|VPA[:\s]|UPI[/-])\s*"
    r"([A-Za-z][\w.&' -]{1,30}?)"
    r"(?:\s+(?:on|via|for|from|ref|bal|using|dated|is|\d{2}[/-])|\.|$)",
    re.IGNORECASE,
)

# --- Date patterns ---
DATE_FORMATS = [
    r"\d{2}[-/]\d{2}[-/]\d{4}",   # 20-04-2026 or 20/04/2026
    r"\d{2}-\w{3}-\d{2,4}",        # 20-Apr-26 or 20-Apr-2026
    r"\d{4}-\d{2}-\d{2}",          # 2026-04-20
]
DATE_RE = re.compile("|".join(f"({p})" for p in DATE_FORMATS))

PARSE_FORMATS = [
    "%d-%m-%Y", "%d/%m/%Y", "%d-%b-%y", "%d-%b-%Y", "%Y-%m-%d",
]


def _parse_amount(text: str):
    """Extract first monetary amount from text."""
    match = AMOUNT_RE.search(text)
    if match:
        return float(match.group(1).replace(",", ""))
    return None


def _parse_type(text: str) -> str:
    """Determine if transaction is debit or credit."""
    text_lower = text.lower()
    for kw in CREDIT_KEYWORDS:
        if kw in text_lower:
            return "credit"
    for kw in DEBIT_KEYWORDS:
        if kw in text_lower:
            return "debit"
    return "debit"  # default assumption


def _parse_merchant(text: str):
    """Extract merchant/payee name."""
    match = MERCHANT_RE.search(text)
    if match:
        return match.group(1).strip().rstrip(".")
    return "Unknown"


def _parse_date(text: str, email_date: str = ""):
    """Extract transaction date from text, fallback to email date."""
    match = DATE_RE.search(text)
    if match:
        date_str = next(g for g in match.groups() if g)
        for fmt in PARSE_FORMATS:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
    # Fallback: use the email's Date header
    if email_date:
        try:
            return parsedate_to_datetime(email_date).date()
        except Exception:
            pass
    return datetime.now().date()


def parse_transaction(body: str, email_date: str = ""):
    """
    Parse a bank email/SMS body into structured transaction data.
    Returns dict with: amount, type, merchant, date — or None if no amount found.
    """
    amount = _parse_amount(body)
    if amount is None:
        return None

    return {
        "amount": amount,
        "type": _parse_type(body),
        "merchant": _parse_merchant(body),
        "date": _parse_date(body, email_date),
    }
