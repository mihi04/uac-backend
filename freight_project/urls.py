"""
freight_project/urls.py  —  Root URL Configuration
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

API = 'api/v1/'

urlpatterns = [
    path('admin/', admin.site.urls),

    # ── Core Modules ──────────────────────────────────────────────────────────
    path(API + 'auth/',         include('apps.authentication.urls')),
    path(API + 'users/',        include('apps.users.urls')),
    path(API + 'customers/',    include('apps.customers.urls')),
    path(API + 'quotations/',   include('apps.quotations.urls')),
    path(API + 'shipments/',    include('apps.shipments.urls')),
    path(API + 'invoices/',     include('apps.invoices.urls')),
    path(API + 'payments/',     include('apps.payments.urls')),
    path(API + 'vendors/',      include('apps.vendors.urls')),
    path(API + 'accounts/',     include('apps.accounts.urls')),
    path(API + 'reports/',      include('apps.reporting.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
