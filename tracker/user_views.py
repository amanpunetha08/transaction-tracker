"""
User authentication + Gmail account management API.
"""
import json
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import GmailAccount


@require_POST
def register(request):
    data = json.loads(request.body)
    username = data.get("username", "").strip()
    password = data.get("password", "")
    email = data.get("email", "").strip()

    if not username or not password:
        return JsonResponse({"error": "Username and password required"}, status=400)
    if User.objects.filter(username=username).exists():
        return JsonResponse({"error": "Username already taken"}, status=400)

    user = User.objects.create_user(username=username, password=password, email=email)
    login(request, user)
    return JsonResponse({"id": user.id, "username": user.username})


@require_POST
def login_view(request):
    data = json.loads(request.body)
    user = authenticate(request, username=data.get("username"), password=data.get("password"))
    if user is None:
        return JsonResponse({"error": "Invalid credentials"}, status=401)
    login(request, user)
    return JsonResponse({"id": user.id, "username": user.username})


@require_POST
def logout_view(request):
    logout(request)
    return JsonResponse({"status": "logged out"})


def me(request):
    if not request.user.is_authenticated:
        return JsonResponse({"authenticated": False})

    accounts = list(
        request.user.gmail_accounts.values("id", "email", "connected", "connected_at")
    )
    for a in accounts:
        a["connected_at"] = a["connected_at"].isoformat()

    return JsonResponse({
        "authenticated": True,
        "id": request.user.id,
        "username": request.user.username,
        "gmail_accounts": accounts,
    })


@require_POST
def add_email(request):
    """Add a Gmail email to the user's account list (not connected yet)."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Not authenticated"}, status=401)

    data = json.loads(request.body)
    email = data.get("email", "").strip().lower()

    if not email or "@" not in email:
        return JsonResponse({"error": "Valid email required"}, status=400)

    if request.user.gmail_accounts.filter(email=email).exists():
        return JsonResponse({"error": "Email already added"}, status=400)

    account = GmailAccount.objects.create(user=request.user, email=email)
    return JsonResponse({"id": account.id, "email": account.email, "connected": False})


@require_POST
def remove_account(request, account_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Not authenticated"}, status=401)

    deleted, _ = request.user.gmail_accounts.filter(id=account_id).delete()
    if not deleted:
        return JsonResponse({"error": "Account not found"}, status=404)
    return JsonResponse({"status": "removed"})
