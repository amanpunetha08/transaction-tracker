from django.contrib import admin
from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["date", "type", "amount", "merchant"]
    list_filter = ["type", "date"]
    search_fields = ["merchant"]
