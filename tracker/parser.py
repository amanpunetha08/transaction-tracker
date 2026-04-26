"""
Transaction parser using Groq LLM (Llama 3.3 70B).
Batches ALL emails into a single API call to minimize usage.
"""
import json
import os
from datetime import datetime
from groq import Groq

SYSTEM_PROMPT = """You extract transaction details from Indian bank emails/SMS. You will receive multiple emails separated by "---EMAIL---". For each email, extract the transaction or mark it as skip.

Return ONLY a JSON array, one object per email, in the same order. No other text.

Each object format:
{"amount": 1925.00, "type": "debit", "merchant": "Swiggy", "date": "2026-04-25"}

Rules:
- amount: number
- type: "debit" or "credit"
- merchant: the APP or PLATFORM or COMPANY through which payment was made
- date: YYYY-MM-DD format

Merchant extraction rules (IMPORTANT):
- If paid via Swiggy/Zomato/Amazon/Flipkart etc, merchant = the app name (e.g. "Swiggy" not the restaurant name)
- If paid via UPI to a person, merchant = person's name + "(UPI Transfer)"
- If NEFT/IMPS to a person, merchant = person's name + "(Bank Transfer)"
- If salary/refund credited, merchant = company name
- For credit card transactions, use the "Info:" field as merchant
- For bill payments (electricity, phone, etc), merchant = the biller name

Type rules:
- "debited", "spent", "paid", "used for a transaction", "transferred" = debit
- "credited", "received", "refund", "cashback", "salary" = credit

If NOT a transaction (OTP, promo, alert without amount), return: {"skip": true}"""


def parse_transactions_batch(emails: list[dict]) -> list[dict | None]:
    """Parse multiple emails in batched LLM calls. Splits into chunks of 10."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or not emails:
        return [None] * len(emails)

    all_results = []
    for i in range(0, len(emails), 10):
        chunk = emails[i:i + 10]
        all_results.extend(_parse_chunk(api_key, chunk))
    return all_results


def _parse_chunk(api_key: str, emails: list[dict]) -> list[dict | None]:
    """Parse a chunk of up to 10 emails in one LLM call."""
    parts = [em.get("body", "")[:800] for em in emails]
    batch_text = "\n---EMAIL---\n".join(parts)

    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": batch_text},
            ],
            temperature=0,
            max_tokens=2000,
        )

        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        results_json = json.loads(raw)
        if not isinstance(results_json, list):
            results_json = [results_json]

        parsed = []
        for i, data in enumerate(results_json):
            if data.get("skip"):
                parsed.append(None)
                continue

            email_date = emails[i].get("date", "") if i < len(emails) else ""
            try:
                d = datetime.strptime(data["date"], "%Y-%m-%d").date()
            except (ValueError, KeyError):
                if email_date:
                    from email.utils import parsedate_to_datetime
                    try:
                        d = parsedate_to_datetime(email_date).date()
                    except Exception:
                        d = datetime.now().date()
                else:
                    d = datetime.now().date()

            parsed.append({
                "amount": float(data.get("amount", 0)),
                "type": data.get("type", "debit"),
                "merchant": data.get("merchant", "Unknown"),
                "date": d,
            })

        # Pad if LLM returned fewer results
        while len(parsed) < len(emails):
            parsed.append(None)
        return parsed

    except Exception:
        return [None] * len(emails)


# Single email fallback (used by management command)
def parse_transaction(body: str, email_date: str = ""):
    results = parse_transactions_batch([{"body": body, "date": email_date}])
    return results[0] if results else None
