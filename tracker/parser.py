"""
Transaction parser — tuned for real Indian bank email formats.
"""
import re
from datetime import datetime
from email.utils import parsedate_to_datetime

# --- Amount ---
AMOUNT_RE = re.compile(r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE)

# --- Type ---
DEBIT_KW = ["debited", "debit", "spent", "withdrawn", "purchase", "paid", "charged", "sent", "used for a transaction", "transferred", "completed", "successful", "payment of"]
CREDIT_KW = ["credited", "credit", "received", "refund", "cashback", "deposited", "reversed", "salary"]

# --- Merchant patterns (ordered by priority) ---
MERCHANT_PATTERNS = [
    # ICICI: "Info: AMAZON PAY IN E COMMERCE"
    re.compile(r"Info[:\s]+([A-Za-z][\w .&/-]{2,50}?)(?:\s*[.\n]|$)", re.IGNORECASE),
    # Kotak: "Sender Name: AMAN PUNETHA"
    re.compile(r"Sender\s+Name[:\s]+([A-Za-z][\w .&/-]{2,50}?)(?:\s*\n|$)", re.IGNORECASE),
    # SBI YONO: "Beneficiary Name aman"
    re.compile(r"Beneficiary\s+Name\s+([A-Za-z][\w .&/-]{2,50}?)(?:\s+Beneficiary|\s*\n|$)", re.IGNORECASE),
    # Kotak: "Remarks : Transfer to Family"
    re.compile(r"Remarks?\s*[:\s]+([A-Za-z][\w .&/-]{2,50}?)(?:\s*\n|$)", re.IGNORECASE),
    # "at Helen's Place" / "at Amazon.in"
    re.compile(r"\bat\s+([A-Za-z][\w .&/'-]{2,40}?)(?:\s+(?:was|on|via|for|ref|using|dated)|[.\n]|$)", re.IGNORECASE),
    # VPA: "to VPA merchant@bank"
    re.compile(r"VPA\s+([A-Za-z][\w.-]+?)@", re.IGNORECASE),
    # UPI: "UPI-Swiggy"
    re.compile(r"UPI[-/]([A-Za-z][\w .&-]{1,30}?)(?:\s*[./]|\s+Ref|\s*$)", re.IGNORECASE),
    # "Transferred to PHONEPE"
    re.compile(r"(?:transferred|paid|sent)\s+to\s+([A-Z][\w .&-]{2,30}?)(?:\s*[.]|\s+(?:IMPS|NEFT|UPI|Ref|If|on)|\s*$)", re.IGNORECASE),
    # "from ZERODHA EQUITY" (credits)
    re.compile(r"(?:by|from)\s+(?:NEFT|IMPS|UPI)\s+(?:from\s+)?([A-Z][\w .&-]{2,30}?)(?:\s*[.]|\s*$)", re.IGNORECASE),
    # "to MERCHANT. IMPS"
    re.compile(r"\bto\s+([A-Z][\w .&-]{2,30}?)(?:\s*[.]|\s+(?:IMPS|NEFT|Ref|If))", re.IGNORECASE),
]

# Skip these as merchant names
SKIP_WORDS = {"your", "account", "a/c", "ac", "bank", "card", "otp", "cvv",
              "anyone", "customer", "dear", "the", "this", "not", "you",
              "be", "do", "never", "please", "click"}

# --- Date patterns ---
DATE_PATTERNS = [
    (re.compile(r"(\w{3}\s+\d{1,2},?\s+\d{4})"), ["%b %d, %Y", "%b %d %Y"]),  # Apr 25, 2026
    (re.compile(r"(\d{2}[-/]\d{2}[-/]\d{4})"), ["%d-%m-%Y", "%d/%m/%Y"]),       # 25-04-2026
    (re.compile(r"(\d{2}-\w{3}-\d{2,4})"), ["%d-%b-%y", "%d-%b-%Y"]),           # 25-Apr-26
    (re.compile(r"(\d{4}-\d{2}-\d{2})"), ["%Y-%m-%d"]),                          # 2026-04-25
]

# --- Spam filter ---
NON_TXN_RE = re.compile(r"(do not share|never share|otp.*password|one.time.password)", re.IGNORECASE)


def _parse_amount(text: str):
    match = AMOUNT_RE.search(text)
    return float(match.group(1).replace(",", "")) if match else None


def _parse_type(text: str) -> str:
    lower = text.lower()
    # Check multi-word phrases first (more specific)
    if "used for a transaction" in lower or "transferred to" in lower:
        return "debit"
    # Then single keywords — check debit first since "credit card" contains "credit"
    for kw in DEBIT_KW:
        if kw in lower:
            return "debit"
    for kw in CREDIT_KW:
        if kw in lower:
            return "credit"
    return "debit"


def _parse_merchant(text: str) -> str:
    for pattern in MERCHANT_PATTERNS:
        match = pattern.search(text)
        if match:
            name = match.group(1).strip().rstrip(".")
            first_word = name.lower().split()[0] if name else ""
            if first_word in SKIP_WORDS:
                continue
            if len(name) >= 2:
                return name
    return "Unknown"


def _parse_date(text: str, email_date: str = ""):
    for regex, formats in DATE_PATTERNS:
        match = regex.search(text)
        if match:
            date_str = match.group(1)
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
    if email_date:
        try:
            return parsedate_to_datetime(email_date).date()
        except Exception:
            pass
    return datetime.now().date()


def parse_transaction(body: str, email_date: str = ""):
    """Parse bank email into transaction data. Returns None if not a real transaction."""
    amount = _parse_amount(body)
    if amount is None:
        return None

    # Skip if the amount only appears in "Available Limit" / "Credit Limit" context
    # but not in a transaction context
    lower = body.lower()
    has_txn_keyword = any(kw in lower for kw in DEBIT_KW + CREDIT_KW)
    if not has_txn_keyword:
        return None

    return {
        "amount": amount,
        "type": _parse_type(body),
        "merchant": _parse_merchant(body),
        "date": _parse_date(body, email_date),
    }
