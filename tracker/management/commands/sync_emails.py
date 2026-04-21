"""
Usage: python manage.py sync_emails --days 30

Connects to Gmail, fetches bank emails, parses transactions, saves to DB.
"""
import os
from django.core.management.base import BaseCommand
from tracker.email_reader import fetch_emails
from tracker.parser import parse_transaction
from tracker.models import Transaction


class Command(BaseCommand):
    help = "Fetch bank emails from Gmail and save parsed transactions"

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30, help="Fetch emails from last N days")

    def handle(self, *args, **options):
        email_addr = os.getenv("EMAIL")
        app_password = os.getenv("APP_PASSWORD")

        if not email_addr or not app_password:
            self.stderr.write("ERROR: Set EMAIL and APP_PASSWORD in .env file")
            return

        self.stdout.write(f"Fetching emails from last {options['days']} days...")
        emails = fetch_emails(email_addr, app_password, days=options["days"])
        self.stdout.write(f"Found {len(emails)} bank emails")

        created = 0
        for em in emails:
            # Skip if we already imported this email
            if Transaction.objects.filter(email_subject=em["subject"]).exists():
                continue

            parsed = parse_transaction(em["body"], em["date"])
            if parsed is None:
                continue

            Transaction.objects.create(
                amount=parsed["amount"],
                type=parsed["type"],
                merchant=parsed["merchant"],
                date=parsed["date"],
                email_subject=em["subject"],
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Done! {created} new transactions saved."))
