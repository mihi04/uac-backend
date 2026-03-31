# 🚢 Smart Freight Revenue Management — Django Backend

A production-ready **Django REST Framework** backend for managing the full
freight operations lifecycle: customers, quotations, shipments, invoices,
payments, vendors, accounts, and reporting.

---

## 🗂️ Project Structure

```
freight_backend/
├── freight_project/            # Django project package
│   ├── settings.py             # All configuration
│   ├── urls.py                 # Root URL config
│   ├── middleware.py           # Audit log + request logging
│   ├── pagination.py           # Standard pagination
│   ├── exceptions.py           # Uniform error envelope
│   ├── base_model.py           # Abstract TimeStampedModel / AuditedModel
│   ├── wsgi.py
│   └── asgi.py
│
├── apps/
│   ├── authentication/         # JWT login / refresh / logout
│   ├── users/                  # User, Role, UserGroup, AuditLog
│   ├── customers/              # Customer CRUD + KYC documents
│   ├── quotations/             # Quotation engine + auto-calc
│   ├── shipments/              # Shipment lifecycle + container tracking
│   ├── invoices/               # Invoice + GST calculation + PDF
│   ├── payments/               # Payment tracking + reconciliation
│   ├── vendors/                # Vendor + rate cards + payables
│   ├── accounts/               # AR / AP dashboards (computed views)
│   └── reporting/              # Revenue / profit / cash flow reports
│
├── manage.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## ⚡ Quick Start

### 1. Clone & Configure
```bash
git clone <repo-url>
cd freight_backend
cp .env.example .env
# Edit .env with your DB credentials, secret key, etc.
```

### 2. Using Docker (recommended)
```bash
docker-compose up --build
```
The API will be available at **http://localhost:8000/api/v1/**

### 3. Manual Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate          # Linux/Mac
# venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Create PostgreSQL database
createdb freight_db

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Create logs directory
mkdir logs

# Run dev server
python manage.py runserver
```

---

## 🗄️ Database Setup (PostgreSQL)

```sql
CREATE USER freight_user WITH PASSWORD 'freight_password';
CREATE DATABASE freight_db OWNER freight_user;
GRANT ALL PRIVILEGES ON DATABASE freight_db TO freight_user;
```

---

## 🔐 API Authentication

All endpoints (except `/auth/login/`) require a **Bearer JWT token**.

```bash
# 1. Login
POST /api/v1/auth/login/
Body: { "email": "admin@example.com", "password": "yourpassword" }

# Response
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "user": { "id": 1, "name": "Admin", "role": "admin" }
}

# 2. Use token in all subsequent requests
Authorization: Bearer eyJ...

# 3. Refresh token
POST /api/v1/auth/refresh/
Body: { "refresh": "eyJ..." }

# 4. Logout (blacklists the token)
POST /api/v1/auth/logout/
Body: { "refresh_token": "eyJ..." }
```

---

## 📡 API Reference

### Authentication
| Method | Endpoint                  | Description         |
|--------|---------------------------|---------------------|
| POST   | `/api/v1/auth/login/`     | Login, get tokens   |
| POST   | `/api/v1/auth/refresh/`   | Refresh access token|
| POST   | `/api/v1/auth/logout/`    | Invalidate token    |
| GET    | `/api/v1/auth/me/`        | Current user info   |

### Users & Roles
| Method | Endpoint                       | Description           |
|--------|--------------------------------|-----------------------|
| GET    | `/api/v1/users/`               | List users            |
| POST   | `/api/v1/users/`               | Create user           |
| GET    | `/api/v1/users/{id}/`          | User detail           |
| PATCH  | `/api/v1/users/{id}/`          | Update user           |
| DELETE | `/api/v1/users/{id}/`          | Deactivate user       |
| POST   | `/api/v1/users/{id}/change-password/` | Change password|
| GET    | `/api/v1/users/me/`            | My profile            |
| GET    | `/api/v1/users/roles/`         | List roles            |
| GET    | `/api/v1/users/groups/`        | List user groups      |

### Customers
| Method | Endpoint                              | Description           |
|--------|---------------------------------------|-----------------------|
| GET    | `/api/v1/customers/`                  | List customers        |
| POST   | `/api/v1/customers/`                  | Create customer       |
| GET    | `/api/v1/customers/{id}/`             | Customer detail       |
| PATCH  | `/api/v1/customers/{id}/`             | Update customer       |
| GET    | `/api/v1/customers/{id}/contacts/`    | List contacts         |
| POST   | `/api/v1/customers/{id}/contacts/`    | Add contact           |
| GET    | `/api/v1/customers/{id}/addresses/`   | List addresses        |
| POST   | `/api/v1/customers/{id}/addresses/`   | Add address           |
| GET    | `/api/v1/customers/{id}/documents/`   | List KYC documents    |
| POST   | `/api/v1/customers/{id}/documents/`   | Upload KYC document   |

### Quotations
| Method | Endpoint                                    | Description              |
|--------|---------------------------------------------|--------------------------|
| GET    | `/api/v1/quotations/`                       | List quotations          |
| POST   | `/api/v1/quotations/`                       | Create quotation         |
| GET    | `/api/v1/quotations/{id}/`                  | Quotation detail         |
| PATCH  | `/api/v1/quotations/{id}/`                  | Update quotation         |
| POST   | `/api/v1/quotations/{id}/send/`             | Mark as sent             |
| POST   | `/api/v1/quotations/{id}/convert-to-shipment/` | Convert to shipment  |
| GET    | `/api/v1/quotations/charge-types/`          | List charge types        |

### Shipments
| Method | Endpoint                                | Description              |
|--------|-----------------------------------------|--------------------------|
| GET    | `/api/v1/shipments/`                    | List shipments           |
| POST   | `/api/v1/shipments/`                    | Create shipment          |
| GET    | `/api/v1/shipments/{id}/`               | Shipment detail          |
| PATCH  | `/api/v1/shipments/{id}/`               | Update shipment          |
| POST   | `/api/v1/shipments/{id}/update-status/` | Update lifecycle status  |
| GET    | `/api/v1/shipments/{id}/containers/`    | List containers          |
| POST   | `/api/v1/shipments/{id}/containers/`    | Add container            |
| GET    | `/api/v1/shipments/{id}/tracking/`      | Tracking events          |
| POST   | `/api/v1/shipments/{id}/create-invoice/`| Create invoice           |

### Invoices
| Method | Endpoint                               | Description           |
|--------|----------------------------------------|-----------------------|
| GET    | `/api/v1/invoices/`                    | List invoices         |
| POST   | `/api/v1/invoices/`                    | Create invoice        |
| GET    | `/api/v1/invoices/{id}/`               | Invoice detail        |
| PATCH  | `/api/v1/invoices/{id}/`               | Update invoice        |
| POST   | `/api/v1/invoices/{id}/issue/`         | Issue invoice         |
| POST   | `/api/v1/invoices/{id}/send-email/`    | Email invoice         |
| GET    | `/api/v1/invoices/{id}/download-pdf/`  | Download PDF          |

### Payments
| Method | Endpoint                               | Description           |
|--------|----------------------------------------|-----------------------|
| GET    | `/api/v1/payments/`                    | List payments         |
| POST   | `/api/v1/payments/`                    | Record payment        |
| GET    | `/api/v1/payments/{id}/`               | Payment detail        |
| POST   | `/api/v1/payments/{id}/confirm/`       | Confirm payment       |
| POST   | `/api/v1/payments/{id}/reconcile/`     | Mark reconciled       |
| GET    | `/api/v1/payments/unreconciled/`       | Unreconciled list     |

### Vendors
| Method | Endpoint                               | Description           |
|--------|----------------------------------------|-----------------------|
| GET    | `/api/v1/vendors/`                     | List vendors          |
| POST   | `/api/v1/vendors/`                     | Create vendor         |
| GET    | `/api/v1/vendors/{id}/rates/`          | Vendor rate cards     |
| POST   | `/api/v1/vendors/{id}/rates/`          | Add rate              |
| GET    | `/api/v1/vendors/payments/`            | Vendor payments       |
| POST   | `/api/v1/vendors/payments/`            | Create vendor payment |
| POST   | `/api/v1/vendors/payments/{id}/approve/`  | Approve payment    |
| POST   | `/api/v1/vendors/payments/{id}/mark-paid/`| Mark paid          |

### Accounts
| Method | Endpoint                                   | Description          |
|--------|--------------------------------------------|----------------------|
| GET    | `/api/v1/accounts/receivable/summary/`     | AR summary           |
| GET    | `/api/v1/accounts/receivable/aging/`       | Aging report         |
| GET    | `/api/v1/accounts/receivable/outstanding/` | Outstanding invoices |
| GET    | `/api/v1/accounts/payable/summary/`        | AP summary           |
| GET    | `/api/v1/accounts/payable/pending/`        | Pending payables     |

### Reports (supports `?from_date=&to_date=`)
| Method | Endpoint                               | Description           |
|--------|----------------------------------------|-----------------------|
| GET    | `/api/v1/reports/dashboard/`           | KPI dashboard         |
| GET    | `/api/v1/reports/revenue/`             | Monthly revenue       |
| GET    | `/api/v1/reports/shipment-profit/`     | Per-shipment P&L      |
| GET    | `/api/v1/reports/cash-flow/`           | Cash flow statement   |
| GET    | `/api/v1/reports/customer-revenue/`    | Revenue by customer   |

---

## 🔒 RBAC Roles

| Role             | Access Level                                  |
|------------------|-----------------------------------------------|
| `super_admin`    | Full access, including admin panel            |
| `admin`          | Full API access                               |
| `manager`        | All modules; no user deletion                 |
| `sales`          | Customers, Quotations, Shipments (read)       |
| `operations`     | Shipments, Containers, Tracking               |
| `accounts`       | Invoices, Payments, AR/AP, Reports            |
| `viewer`         | Read-only across all modules                  |

---

## 🧩 Business Rules Implemented

- **Credit limit check** — `Customer.available_credit` property; enforced at payment level
- **GST auto-calculation** — IGST (interstate) or CGST+SGST (intrastate) split in Invoice
- **Quotation → Shipment conversion** — only `APPROVED` quotations can be converted
- **Payment validation** — payment amount cannot exceed invoice `balance_due`
- **Invoice status auto-update** — transitions to `PARTIAL` or `PAID` after payment confirmation
- **Atomic payment confirm** — updates Invoice + Customer outstanding in a single DB transaction
- **Double-entry transactions** — auto-created on every payment (Debit: Bank, Credit: AR)
- **Soft deletes** — Users, Customers, Vendors are deactivated, not deleted
- **Unique number generation** — auto-generated for Quotations, Shipments, Invoices, Payments

---

## 🧪 Running Tests

```bash
pytest
pytest apps/customers/          # run single app
pytest -v --tb=short            # verbose output
pytest --cov=apps               # with coverage
```

---

## 🚀 Production Checklist

- [ ] Set `DEBUG=False` in `.env`
- [ ] Generate a strong `SECRET_KEY` (use `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`)
- [ ] Set `ALLOWED_HOSTS` to your domain
- [ ] Configure real SMTP credentials for email
- [ ] Switch `FILE_STORAGE_BACKEND=s3` and set AWS credentials
- [ ] Run behind **Nginx** (reverse proxy) + **Gunicorn**
- [ ] Enable HTTPS / SSL certificates (Let's Encrypt)
- [ ] Set up **Celery + Redis** for async tasks (email, PDF generation)
- [ ] Configure database backups
- [ ] Set up monitoring (Sentry / Datadog)

---

## 📦 Tech Stack

| Layer        | Technology                          |
|--------------|-------------------------------------|
| Framework    | Django 5.0 + Django REST Framework  |
| Auth         | JWT via `djangorestframework-simplejwt` |
| Database     | PostgreSQL 16                       |
| File Storage | Local or AWS S3                     |
| PDF          | ReportLab (swap for WeasyPrint)     |
| Containerisation | Docker + Docker Compose         |
| Task Queue   | Celery + Redis (optional)           |
