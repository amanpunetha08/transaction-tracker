"""
Gmail API email reader.
Uses OAuth2 tokens (from session) to read emails — no passwords needed.
"""
import base64
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# Same bank sender keywords as before
BANK_SENDERS = [
    "alerts@", "noreply@", "transaction@", "notify@",
    "hdfcbank", "icicibank", "sbi", "axisbank", "kotak",
    "paytm", "phonepe", "gpay", "razorpay", "cred",
]


def _build_service(token_data: dict):
    """Build Gmail API service from stored tokens."""
    creds = Credentials(
        token=token_data["token"],
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data["token_uri"],
        client_id=token_data["client_id"],
        client_secret=token_data["client_secret"],
        scopes=token_data["scopes"],
    )
    return build("gmail", "v1", credentials=creds)


def _get_body(payload: dict) -> str:
    """Extract plain text body from Gmail API message payload."""
    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain" and "data" in part.get("body", {}):
                return base64.urlsafe_b64decode(part["body"]["data"]).decode(errors="ignore")
            # Check nested parts
            text = _get_body(part)
            if text:
                return text
    elif "data" in payload.get("body", {}):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode(errors="ignore")
    return ""


def fetch_emails(token_data: dict, days: int = 30) -> list[dict]:
    """
    Fetch bank transaction emails using Gmail API.
    Returns list of dicts: {subject, sender, date, body}
    """
    service = _build_service(token_data)

    since = (datetime.now() - timedelta(days=days)).strftime("%Y/%m/%d")
    query = f"after:{since}"

    results = []
    page_token = None

    while True:
        resp = service.users().messages().list(
            userId="me", q=query, maxResults=100, pageToken=page_token
        ).execute()

        for msg_meta in resp.get("messages", []):
            msg = service.users().messages().get(
                userId="me", id=msg_meta["id"], format="full"
            ).execute()

            headers = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}
            sender = headers.get("from", "").lower()

            # Only process bank/payment emails
            if not any(kw in sender for kw in BANK_SENDERS):
                continue

            results.append({
                "subject": headers.get("subject", ""),
                "sender": sender,
                "date": headers.get("date", ""),
                "body": _get_body(msg["payload"]),
            })

        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return results
