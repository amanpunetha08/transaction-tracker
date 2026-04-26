"""
Gmail API email reader — optimized.
Filters bank emails server-side using Gmail search, extracts text from HTML.
"""
import re
import base64
from html import unescape
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

BANK_QUERY = (
    "from:("
    # Major Private Banks
    "hdfcbank OR icicibank OR axisbank OR kotak OR indusind OR yesbank OR idfcfirst OR "
    "federalbank OR rblbank OR bandhanbank OR idbibank OR "
    # Public Sector Banks
    "sbi OR pnb OR bankofbaroda OR canarabank OR unionbank OR indianbank OR "
    "bankofmaharashtra OR centralbank OR indianoverseas OR ucobank OR "
    # Payment Apps & Wallets
    "paytm OR phonepe OR gpay OR razorpay OR cred OR amazonpay OR "
    "mobikwik OR freecharge OR simpl OR lazypay OR slice OR jupiter OR fi.money OR "
    # Common sender patterns
    "alerts OR noreply OR transaction OR notify OR donotreply"
    ") "
    "subject:(transaction OR debited OR credited OR payment OR spent OR received "
    "OR refund OR success OR declined OR UPI OR transfer OR alert OR debit OR credit "
    "OR txn OR withdrawn OR purchase OR EMI OR autopay OR mandate OR bill)"
)

# Subjects that are NOT transactions — skip before sending to LLM
SKIP_SUBJECTS = [
    "login alert", "otp", "password", "verify", "welcome",
    "registration success", "e-mandate set", "mandate registration",
    "credit score", "credit limit", "loan offer", "pre-approved",
    "reward", "cashback offer", "congratulations", "congrats",
    "avail rs", "avail ₹", "price drop", "guide to",
    "overdue", "reminder", "upcoming", "due date",
    "newsletter", "unsubscribe",
]


def _is_skip_subject(subject: str) -> bool:
    """Check if email subject indicates a non-transaction email."""
    lower = subject.lower()
    return any(skip in lower for skip in SKIP_SUBJECTS)


def _build_service(token_data: dict):
    creds = Credentials(
        token=token_data["token"],
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data["token_uri"],
        client_id=token_data["client_id"],
        client_secret=token_data["client_secret"],
        scopes=token_data["scopes"],
    )
    return build("gmail", "v1", credentials=creds)


def _html_to_text(html: str) -> str:
    """Strip HTML tags and decode entities to get plain text."""
    # Remove style and script blocks
    text = re.sub(r"<(style|script)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # Replace <br>, <p>, <div>, <tr> with newlines
    text = re.sub(r"<br\s*/?>|</p>|</div>|</tr>|</td>", "\n", text, flags=re.IGNORECASE)
    # Remove all remaining tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Decode HTML entities
    text = unescape(text)
    # Clean up whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def _get_body(payload: dict) -> str:
    """Extract text body from Gmail message payload. Handles both plain text and HTML."""
    plain = ""
    html = ""

    def _walk(part):
        nonlocal plain, html
        mime = part.get("mimeType", "")
        data = part.get("body", {}).get("data", "")

        if mime == "text/plain" and data:
            plain = base64.urlsafe_b64decode(data).decode(errors="ignore")
        elif mime == "text/html" and data:
            html = base64.urlsafe_b64decode(data).decode(errors="ignore")

        for sub in part.get("parts", []):
            _walk(sub)

    _walk(payload)

    # Prefer plain text, fall back to HTML→text conversion
    if plain.strip():
        return plain
    if html.strip():
        return _html_to_text(html)
    return ""


def fetch_emails(token_data: dict, days: int = 30) -> list[dict]:
    service = _build_service(token_data)

    since = (datetime.now() - timedelta(days=days)).strftime("%Y/%m/%d")
    query = f"after:{since} {BANK_QUERY}"

    msg_ids = []
    page_token = None
    while True:
        resp = service.users().messages().list(
            userId="me", q=query, maxResults=100, pageToken=page_token
        ).execute()
        msg_ids.extend(m["id"] for m in resp.get("messages", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    results = []
    for msg_id in msg_ids:
        msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
        headers = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}

        body = _get_body(msg["payload"]) or msg.get("snippet", "")

        subject = headers.get("subject", "")

        # Skip non-transaction emails before sending to LLM
        if _is_skip_subject(subject):
            continue

        results.append({
            "msg_id": msg_id,
            "subject": subject,
            "sender": headers.get("from", ""),
            "date": headers.get("date", ""),
            "body": body,
        })

    return results
