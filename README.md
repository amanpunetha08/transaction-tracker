# Transaction Tracker — Backend

Django REST API that reads bank transaction emails from Gmail and stores parsed transactions in SQLite.

## Setup

```bash
cd transaction-tracker
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `.env` from template:
```bash
cp .env.example .env
# Edit .env with your Gmail address and App Password
```

Run migrations and start server:
```bash
python manage.py migrate
python manage.py runserver
```

## Sync Emails

```bash
python manage.py sync_emails          # last 30 days
python manage.py sync_emails --days 7 # last 7 days
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/summary/?days=30` | GET | Total debit/credit + top merchants |
| `/api/transactions/?days=30&type=debit` | GET | Transaction list with filters |
| `/admin/` | GET | Django admin panel |

## Gmail App Password

1. Enable 2FA on your Google account
2. Go to https://myaccount.google.com/apppasswords
3. Generate an app password
4. Add it to `.env` as `APP_PASSWORD`
