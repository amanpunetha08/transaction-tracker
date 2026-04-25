"""
OAuth2 flow:
1. User visits /auth/login/ → redirected to Google consent screen
2. User clicks "Allow" → Google redirects to /auth/callback/
3. We exchange the code for tokens → store in session
4. Now we can call Gmail API with the access token
"""
import os
import json
from django.http import JsonResponse
from django.shortcuts import redirect
from google_auth_oauthlib.flow import Flow

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
REDIRECT_URI = "http://localhost:8000/auth/callback/"


def _get_flow():
    """Build OAuth2 flow from .env credentials."""
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


def auth_login(request):
    """Redirect user to Google consent screen."""
    flow = _get_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",  # gives us a refresh token
    )
    request.session["oauth_state"] = state
    return redirect(auth_url)


def auth_callback(request):
    """Google redirects here after user clicks Allow."""
    flow = _get_flow()
    flow.fetch_token(authorization_response=request.build_absolute_uri())

    credentials = flow.credentials
    # Store tokens in session
    request.session["google_tokens"] = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": list(credentials.scopes),
    }

    # Redirect to frontend
    return redirect("http://localhost:5173/")


def auth_status(request):
    """Check if user is authenticated."""
    is_authed = "google_tokens" in request.session
    return JsonResponse({"authenticated": is_authed})


def auth_logout(request):
    """Clear stored tokens."""
    request.session.flush()
    return JsonResponse({"status": "logged out"})
