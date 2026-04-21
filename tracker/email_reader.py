"""
Gmail IMAP email reader.
Connects to Gmail, searches for bank transaction emails, returns raw text.
Uses only Python standard library — no extra packages needed.
"""
import imaplib  # IMAP protocol — to connect & search emails
import email    # Parse raw email bytes into readable parts
from email.header import decode_header
import os
from datetime import datetime, timedelta


# Gmail IMAP server details (same for everyone)
IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993  # SSL port

# Common bank sender keywords to filter emails
BANK_SENDERS = [
    "alerts@", "noreply@", "transaction@", "notify@",
    "hdfcbank", "icicibank", "sbi", "axisbank", "kotak",
    "paytm", "phonepe", "gpay", "razorpay", "cred",
]


def connect(email_addr: str, app_password: str):
    """Login to Gmail via IMAP. Returns the connection object."""
    conn = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    conn.login(email_addr, app_password)
    return conn


def _get_email_text(msg):
    """Extract plain text body from an email message."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(errors="ignore")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode(errors="ignore")
    return ""


def _decode_subject(msg):
    """Decode email subject which may be encoded."""
    subject = msg.get("Subject", "")
    decoded_parts = decode_header(subject)
    result = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or "utf-8", errors="ignore"))
        else:
            result.append(part)
    return " ".join(result)


def fetch_emails(email_addr: str, app_password: str, days: int = 30):
    """
    Fetch bank transaction emails from the last N days.
    Returns list of dicts: {subject, sender, date, body}
    """
    conn = connect(email_addr, app_password)
    conn.select("INBOX")

    # Search for emails from the last N days
    since_date = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
    _, message_ids = conn.search(None, f'(SINCE "{since_date}")')

    results = []
    for msg_id in message_ids[0].split():
        _, msg_data = conn.fetch(msg_id, "(RFC822)")
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)

        sender = msg.get("From", "").lower()
        # Only process emails that look like bank/payment alerts
        if not any(kw in sender for kw in BANK_SENDERS):
            continue

        results.append({
            "subject": _decode_subject(msg),
            "sender": sender,
            "date": msg.get("Date", ""),
            "body": _get_email_text(msg),
        })

    conn.logout()
    return results
