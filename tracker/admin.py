from django.contrib import admin
from .models import GmailAccount, Transaction


@admin.register(GmailAccount)
class GmailAccountAdmin(admin.ModelAdmin):
    list_display = ["email", "user", "connected_at"]


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["date", "type", "amount", "merchant", "user", "gmail_account"]
    list_filter = ["type", "date", "user"]
    search_fields = ["merchant"]
