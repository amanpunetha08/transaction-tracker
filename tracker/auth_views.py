"""
OAuth2 flow for CONNECTING a specific Gmail account.
User adds email first, then clicks "Connect" which triggers OAuth for that email.
"""
import os
from django.http import JsonResponse
from django.shortcuts import redirect
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from .models import GmailAccount

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
REDIRECT_URI = "http://localhost:8000/auth/callback/"


def _get_flow():
    client_config = {
        "web": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI],
        }
    }
    flow = Flow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = REDIRECT_URI
    return flow


def auth_connect(request, account_id):
    """Start OAuth for a specific Gmail account. Shows Google account picker with hint."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login first"}, status=401)

    try:
        account = request.user.gmail_accounts.get(id=account_id)
    except GmailAccount.DoesNotExist:
        return JsonResponse({"error": "Account not found"}, status=404)

    flow = _get_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent select_account",
        login_hint=account.email,  # pre-select this email in Google picker
    )
    request.session["oauth_state"] = state
    request.session["oauth_account_id"] = account.id
    return redirect(auth_url)


def auth_callback(request):
    """Google redirects here. Save tokens to the specific GmailAccount."""
    if not request.user.is_authenticated:
        return redirect("http://localhost:5173/")

    account_id = request.session.pop("oauth_account_id", None)
    if not account_id:
        return redirect("http://localhost:5173/accounts")

    flow = _get_flow()
    flow.fetch_token(authorization_response=request.build_absolute_uri())
    credentials = flow.credentials

    # Verify the Gmail address matches
    service = build("gmail", "v1", credentials=credentials)
    profile = service.users().getProfile(userId="me").execute()
    gmail_email = profile["emailAddress"].lower()

    try:
        account = request.user.gmail_accounts.get(id=account_id)
    except GmailAccount.DoesNotExist:
        return redirect("http://localhost:5173/accounts")

    # Update with tokens — even if email doesn't match, save what they authorized
    account.email = gmail_email
    account.access_token = credentials.token
    account.refresh_token = credentials.refresh_token or ""
    account.client_id = credentials.client_id
    account.client_secret = credentials.client_secret
    account.scopes = ",".join(credentials.scopes)
    account.connected = True
    account.save()

    return redirect("http://localhost:5173/accounts")
