from datetime import date, timedelta
from django.db.models import Sum
from django.http import JsonResponse
from .models import Transaction
from .email_reader import fetch_emails
from .parser import parse_transaction


def api_summary(request):
    """JSON API: spending summary for dashboard charts."""
    days = int(request.GET.get("days", 30))
    since = date.today() - timedelta(days=days)
    qs = Transaction.objects.filter(date__gte=since)

    total_debit = qs.filter(type="debit").aggregate(s=Sum("amount"))["s"] or 0
    total_credit = qs.filter(type="credit").aggregate(s=Sum("amount"))["s"] or 0

    by_merchant = (
        qs.filter(type="debit")
        .values("merchant")
        .annotate(total=Sum("amount"))
        .order_by("-total")[:10]
    )

    return JsonResponse({
        "total_debit": float(total_debit),
        "total_credit": float(total_credit),
        "by_merchant": list(by_merchant),
    })


def api_transactions(request):
    """JSON API: list of transactions with optional filters."""
    days = int(request.GET.get("days", 30))
    tx_type = request.GET.get("type", "")
    since = date.today() - timedelta(days=days)

    qs = Transaction.objects.filter(date__gte=since)
    if tx_type in ("debit", "credit"):
        qs = qs.filter(type=tx_type)

    data = list(qs.values("id", "amount", "type", "merchant", "date"))
    for item in data:
        item["amount"] = float(item["amount"])
        item["date"] = item["date"].isoformat()
    return JsonResponse({"transactions": data})


def api_sync(request):
    """Sync emails using OAuth2 tokens from session."""
    tokens = request.session.get("google_tokens")
    if not tokens:
        return JsonResponse({"error": "Not authenticated. Please sign in with Google."}, status=401)

    days = int(request.GET.get("days", 30))
    emails = fetch_emails(tokens, days=days)

    created = 0
    for em in emails:
        if Transaction.objects.filter(email_subject=em["subject"]).exists():
            continue
        parsed = parse_transaction(em["body"], em["date"])
        if parsed is None:
            continue
        Transaction.objects.create(
            amount=parsed["amount"],
            type=parsed["type"],
            merchant=parsed["merchant"],
            date=parsed["date"],
            email_subject=em["subject"],
        )
        created += 1

    return JsonResponse({"synced": created, "total_emails": len(emails)})
