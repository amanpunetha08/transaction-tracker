from django.urls import path
from . import views, auth_views

urlpatterns = [
    # Auth
    path("auth/login/", auth_views.auth_login, name="auth_login"),
    path("auth/callback/", auth_views.auth_callback, name="auth_callback"),
    path("auth/status/", auth_views.auth_status, name="auth_status"),
    path("auth/logout/", auth_views.auth_logout, name="auth_logout"),
    # API
    path("api/summary/", views.api_summary, name="api_summary"),
    path("api/transactions/", views.api_transactions, name="api_transactions"),
    path("api/sync/", views.api_sync, name="api_sync"),
]
