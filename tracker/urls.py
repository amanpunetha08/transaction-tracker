from django.urls import path
from . import views

urlpatterns = [
    path("api/summary/", views.api_summary, name="api_summary"),
    path("api/transactions/", views.api_transactions, name="api_transactions"),
]
