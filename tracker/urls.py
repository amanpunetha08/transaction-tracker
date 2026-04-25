from django.urls import path
from . import views, auth_views, user_views

urlpatterns = [
    # User auth
    path("api/register/", user_views.register, name="register"),
    path("api/login/", user_views.login_view, name="login"),
    path("api/logout/", user_views.logout_view, name="logout"),
    path("api/me/", user_views.me, name="me"),
    # Gmail account management
    path("api/accounts/add/", user_views.add_email, name="add_email"),
    path("api/accounts/<int:account_id>/remove/", user_views.remove_account, name="remove_account"),
    path("auth/connect/<int:account_id>/", auth_views.auth_connect, name="auth_connect"),
    path("auth/callback/", auth_views.auth_callback, name="auth_callback"),
    # Data
    path("api/summary/", views.api_summary, name="api_summary"),
    path("api/transactions/", views.api_transactions, name="api_transactions"),
    path("api/sync/", views.api_sync, name="api_sync"),
]
