from django.conf import settings
from django.db import models


class GmailAccount(models.Model):
    """A Gmail account added by user. May or may not be connected via OAuth yet."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="gmail_accounts")
    email = models.EmailField()
    connected = models.BooleanField(default=False)
    # OAuth2 tokens (filled after connecting)
    access_token = models.TextField(blank=True, default="")
    refresh_token = models.TextField(blank=True, default="")
    token_uri = models.URLField(default="https://oauth2.googleapis.com/token")
    client_id = models.CharField(max_length=300, blank=True, default="")
    client_secret = models.CharField(max_length=300, blank=True, default="")
    scopes = models.TextField(default="https://www.googleapis.com/auth/gmail.readonly")
    connected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "email")

    def __str__(self):
        return f"{self.email} ({self.user.username})"

    def to_token_dict(self):
        """Convert to dict format expected by email_reader."""
        return {
            "token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_uri": self.token_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scopes": self.scopes.split(","),
        }


class Transaction(models.Model):
    """A single bank transaction parsed from email."""
    TYPE_CHOICES = [("debit", "Debit"), ("credit", "Credit")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="transactions")
    gmail_account = models.ForeignKey(GmailAccount, on_delete=models.SET_NULL, null=True, related_name="transactions")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    type = models.CharField(max_length=6, choices=TYPE_CHOICES)
    merchant = models.CharField(max_length=200)
    date = models.DateField()
    email_subject = models.CharField(max_length=500, blank=True)
    gmail_msg_id = models.CharField(max_length=100, blank=True, default="")
    ref_number = models.CharField(max_length=100, blank=True, default="")
    is_duplicate = models.BooleanField(default=False)
    is_dismissed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.type} ₹{self.amount} - {self.merchant} ({self.date})"
