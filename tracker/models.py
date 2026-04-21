from django.db import models


class Transaction(models.Model):
    """A single bank transaction parsed from email."""

    TYPE_CHOICES = [("debit", "Debit"), ("credit", "Credit")]

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    type = models.CharField(max_length=6, choices=TYPE_CHOICES)
    merchant = models.CharField(max_length=200)
    date = models.DateField()
    # Store email subject as unique key to avoid duplicate imports
    email_subject = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.type} ₹{self.amount} - {self.merchant} ({self.date})"
