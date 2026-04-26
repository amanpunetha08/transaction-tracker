from datetime import date, timedelta
from django.db.models import Sum
from django.http import JsonResponse
from .models import Transaction, GmailAccount
from .email_reader import fetch_emails
from .parser import parse_transactions_batch


def _require_auth(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Not authenticated"}, status=401)
    return None


def api_summary(request):
    """Spending summary filtered by logged-in user."""
    err = _require_auth(request)
    if err:
        return err

    days = int(request.GET.get("days", 30))
    account_id = request.GET.get("account")
    since = date.today() - timedelta(days=days)

    qs = Transaction.objects.filter(user=request.user, date__gte=since, is_dismissed=False)
    if account_id:
        qs = qs.filter(gmail_account_id=account_id)

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
    """Transaction list filtered by logged-in user."""
    err = _require_auth(request)
    if err:
        return err

    days = int(request.GET.get("days", 30))
    tx_type = request.GET.get("type", "")
    account_id = request.GET.get("account")
    since = date.today() - timedelta(days=days)

    qs = Transaction.objects.filter(user=request.user, date__gte=since, is_dismissed=False)
    if tx_type in ("debit", "credit"):
        qs = qs.filter(type=tx_type)
    if account_id:
        qs = qs.filter(gmail_account_id=account_id)

    data = list(qs.values("id", "amount", "type", "merchant", "date", "is_duplicate", "gmail_account__email"))
    for item in data:
        item["amount"] = float(item["amount"])
        item["date"] = item["date"].isoformat()
        item["account_email"] = item.pop("gmail_account__email", "")
    return JsonResponse({"transactions": data})


def api_sync(request):
    """Sync emails from ALL connected Gmail accounts."""
    err = _require_auth(request)
    if err:
        return err

    days = int(request.GET.get("days", 30))
    accounts = GmailAccount.objects.filter(user=request.user, connected=True)

    if not accounts.exists():
        return JsonResponse({"error": "No Gmail accounts connected. Add one first."}, status=400)

    total_created = 0
    total_emails = 0
    results = []

    for account in accounts:
        try:
            emails = fetch_emails(account.to_token_dict(), days=days)
            # Filter out already-imported emails by Gmail message ID
            new_emails = [em for em in emails if not Transaction.objects.filter(user=request.user, gmail_msg_id=em["msg_id"]).exists()]

            # One LLM call for all new emails from this account
            parsed_list = parse_transactions_batch(new_emails)

            created = 0
            for em, parsed in zip(new_emails, parsed_list):
                if parsed is None:
                    continue
                # Dedup: same ref number = same transaction
                # Fallback: no ref but same amount + type + date + merchant = likely duplicate
                ref = parsed.get("ref", "")
                if ref:
                    is_dup = Transaction.objects.filter(user=request.user, ref_number=ref).exists()
                else:
                    is_dup = Transaction.objects.filter(
                        user=request.user,
                        amount=parsed["amount"],
                        type=parsed["type"],
                        date=parsed["date"],
                        merchant=parsed["merchant"],
                    ).exists()

                Transaction.objects.create(
                    user=request.user,
                    gmail_account=account,
                    amount=parsed["amount"],
                    type=parsed["type"],
                    merchant=parsed["merchant"],
                    date=parsed["date"],
                    email_subject=em["subject"],
                    gmail_msg_id=em["msg_id"],
                    ref_number=ref,
                    is_duplicate=is_dup,
                )
                created += 1

            total_created += created
            total_emails += len(emails)
            results.append({"email": account.email, "synced": created, "emails_found": len(emails)})
        except Exception as e:
            results.append({"email": account.email, "error": str(e)})

    return JsonResponse({
        "total_synced": total_created,
        "total_emails": total_emails,
        "accounts": results,
    })


def api_dismiss(request, txn_id):
    """Dismiss a duplicate transaction."""
    err = _require_auth(request)
    if err:
        return err
    updated = Transaction.objects.filter(user=request.user, id=txn_id).update(is_dismissed=True)
    if not updated:
        return JsonResponse({"error": "Transaction not found"}, status=404)
    return JsonResponse({"status": "dismissed"})


def api_keep(request, txn_id):
    """Mark a flagged transaction as not duplicate."""
    err = _require_auth(request)
    if err:
        return err
    updated = Transaction.objects.filter(user=request.user, id=txn_id).update(is_duplicate=False)
    if not updated:
        return JsonResponse({"error": "Transaction not found"}, status=404)
    return JsonResponse({"status": "kept"})
