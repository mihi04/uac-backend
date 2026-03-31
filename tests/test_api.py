"""
tests/test_api.py
Comprehensive test suite for the Freight Revenue Management backend.
Run: pytest tests/ -v
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_role(db):
    from apps.users.models import Role
    role, _ = Role.objects.get_or_create(name='admin', defaults={'description': 'Admin'})
    return role


@pytest.fixture
def admin_user(db, admin_role):
    user = User.objects.create_user(
        email='admin@freight.test',
        password='testpass123',
        name='Admin User',
        role=admin_role,
        is_staff=True,
    )
    return user


@pytest.fixture
def auth_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def customer(db, admin_user):
    from apps.customers.models import Customer
    return Customer.objects.create(
        company_name='Test Exports Pvt Ltd',
        business_type='exporter',
        gst='27AABCU9603R1ZX',
        pan='AABCU9603R',
        credit_limit=Decimal('500000.00'),
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def vendor(db, admin_user):
    from apps.vendors.models import Vendor
    return Vendor.objects.create(
        name='Ocean Lines Ltd',
        service_type='shipping_line',
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def quotation(db, customer, admin_user):
    from apps.quotations.models import Quotation
    return Quotation.objects.create(
        customer=customer,
        origin='Mumbai, India',
        destination='Rotterdam, Netherlands',
        mode='sea_fcl',
        currency='INR',
        gst_percent=Decimal('18.00'),
        status='draft',
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def approved_quotation(db, quotation):
    quotation.status = 'approved'
    quotation.save()
    return quotation


@pytest.fixture
def shipment(db, approved_quotation, customer, admin_user):
    from apps.shipments.models import Shipment
    return Shipment.objects.create(
        customer=customer,
        quotation=approved_quotation,
        mode='sea_fcl',
        origin='Mumbai, India',
        destination='Rotterdam, Netherlands',
        selling_amount=Decimal('150000.00'),
        buying_amount=Decimal('110000.00'),
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def invoice(db, shipment, customer, admin_user):
    from apps.invoices.models import Invoice
    inv = Invoice.objects.create(
        customer=customer,
        shipment=shipment,
        due_date=date.today() + timedelta(days=30),
        currency='INR',
        is_interstate=True,
        igst_percent=Decimal('18.00'),
        created_by=admin_user,
        updated_by=admin_user,
    )
    return inv


# =============================================================================
# AUTHENTICATION TESTS
# =============================================================================

@pytest.mark.django_db
class TestAuthentication:

    def test_login_success(self, api_client, admin_user):
        resp = api_client.post('/api/v1/auth/login/', {
            'email': 'admin@freight.test',
            'password': 'testpass123',
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK
        assert 'access_token'  in resp.data
        assert 'refresh_token' in resp.data
        assert resp.data['user']['email'] == 'admin@freight.test'

    def test_login_wrong_password(self, api_client, admin_user):
        resp = api_client.post('/api/v1/auth/login/', {
            'email': 'admin@freight.test',
            'password': 'wrongpassword',
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_inactive_user(self, api_client, admin_user):
        admin_user.is_active = False
        admin_user.save()
        resp = api_client.post('/api/v1/auth/login/', {
            'email': 'admin@freight.test',
            'password': 'testpass123',
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_protected_endpoint_without_token(self, api_client):
        resp = api_client.get('/api/v1/customers/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_me_endpoint(self, auth_client, admin_user):
        resp = auth_client.get('/api/v1/auth/me/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['email'] == admin_user.email


# =============================================================================
# CUSTOMER TESTS
# =============================================================================

@pytest.mark.django_db
class TestCustomers:

    def test_list_customers(self, auth_client, customer):
        resp = auth_client.get('/api/v1/customers/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['count'] >= 1

    def test_create_customer(self, auth_client):
        resp = auth_client.post('/api/v1/customers/', {
            'company_name': 'New Imports Co',
            'business_type': 'importer',
            'gst': '29AATFB0197N1Z1',
            'pan': 'AATFB0197N',
            'credit_limit': '200000.00',
            'credit_days': 45,
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['company_name'] == 'New Imports Co'

    def test_create_customer_invalid_gst(self, auth_client):
        resp = auth_client.post('/api/v1/customers/', {
            'company_name': 'Bad GST Co',
            'gst': 'INVALID_GST',
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_retrieve_customer(self, auth_client, customer):
        resp = auth_client.get(f'/api/v1/customers/{customer.id}/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['company_name'] == customer.company_name

    def test_soft_delete_customer(self, auth_client, customer):
        resp = auth_client.delete(f'/api/v1/customers/{customer.id}/')
        assert resp.status_code == status.HTTP_200_OK
        customer.refresh_from_db()
        assert customer.status == 'inactive'

    def test_add_contact(self, auth_client, customer):
        resp = auth_client.post(f'/api/v1/customers/{customer.id}/contacts/', {
            'name': 'John Doe',
            'designation': 'Manager',
            'phone': '+919876543210',
            'email': 'john@testexports.com',
            'is_primary': True,
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED

    def test_add_address(self, auth_client, customer):
        resp = auth_client.post(f'/api/v1/customers/{customer.id}/addresses/', {
            'address_type': 'billing',
            'address_line': '123 Test Street',
            'city': 'Mumbai',
            'state': 'Maharashtra',
            'country': 'India',
            'pin_code': '400001',
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED

    def test_available_credit(self, customer):
        assert customer.available_credit == customer.credit_limit


# =============================================================================
# QUOTATION TESTS
# =============================================================================

@pytest.mark.django_db
class TestQuotations:

    def test_create_quotation(self, auth_client, customer):
        resp = auth_client.post('/api/v1/quotations/', {
            'customer': customer.id,
            'origin': 'Chennai, India',
            'destination': 'Hamburg, Germany',
            'mode': 'sea_fcl',
            'gst_percent': '18.00',
            'currency': 'INR',
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['quotation_number'].startswith('QT')

    def test_quotation_auto_number(self, quotation):
        assert quotation.quotation_number.startswith('QT')
        assert len(quotation.quotation_number) > 8

    def test_send_quotation(self, auth_client, quotation):
        resp = auth_client.post(f'/api/v1/quotations/{quotation.id}/send/')
        assert resp.status_code == status.HTTP_200_OK
        quotation.refresh_from_db()
        assert quotation.status == 'sent'

    def test_cannot_send_non_draft(self, auth_client, approved_quotation):
        resp = auth_client.post(f'/api/v1/quotations/{approved_quotation.id}/send/')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_convert_to_shipment(self, auth_client, approved_quotation):
        resp = auth_client.post(
            f'/api/v1/quotations/{approved_quotation.id}/convert-to-shipment/'
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert 'shipment_id' in resp.data
        approved_quotation.refresh_from_db()
        assert approved_quotation.status == 'converted'

    def test_cannot_convert_draft(self, auth_client, quotation):
        resp = auth_client.post(
            f'/api/v1/quotations/{quotation.id}/convert-to-shipment/'
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# SHIPMENT TESTS
# =============================================================================

@pytest.mark.django_db
class TestShipments:

    def test_list_shipments(self, auth_client, shipment):
        resp = auth_client.get('/api/v1/shipments/')
        assert resp.status_code == status.HTTP_200_OK

    def test_shipment_profit(self, shipment):
        assert shipment.profit == Decimal('40000.00')
        assert shipment.profit_margin == pytest.approx(26.67, abs=0.1)

    def test_update_status(self, auth_client, shipment):
        from django.utils import timezone
        resp = auth_client.post(f'/api/v1/shipments/{shipment.id}/update-status/', {
            'status': 'in_transit',
            'location': 'High Seas',
            'description': 'Vessel departed Mumbai port',
            'event_date': timezone.now().isoformat(),
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK
        shipment.refresh_from_db()
        assert shipment.status == 'in_transit'

    def test_invalid_status(self, auth_client, shipment):
        from django.utils import timezone
        resp = auth_client.post(f'/api/v1/shipments/{shipment.id}/update-status/', {
            'status': 'flying_through_space',
            'event_date': timezone.now().isoformat(),
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_add_container(self, auth_client, shipment):
        resp = auth_client.post(f'/api/v1/shipments/{shipment.id}/containers/', {
            'container_type': '40HC',
            'container_number': 'MSCU1234567',
            'seal_number': 'SEAL001',
            'gross_weight': '25000.000',
            'cbm': '67.500',
            'packages': 120,
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED

    def test_tracking_events(self, auth_client, shipment):
        resp = auth_client.get(f'/api/v1/shipments/{shipment.id}/tracking/')
        assert resp.status_code == status.HTTP_200_OK


# =============================================================================
# INVOICE TESTS
# =============================================================================

@pytest.mark.django_db
class TestInvoices:

    def test_invoice_auto_number(self, invoice):
        assert invoice.invoice_number.startswith('INV')

    def test_invoice_gst_calculation(self, invoice):
        from apps.invoices.models import InvoiceItem
        InvoiceItem.objects.create(
            invoice=invoice,
            description='Ocean Freight – 40HC',
            quantity=Decimal('1'),
            unit='container',
            unit_price=Decimal('100000.00'),
            amount=Decimal('100000.00'),
        )
        invoice.refresh_from_db()
        assert invoice.subtotal    == Decimal('100000.00')
        assert invoice.igst_amount == Decimal('18000.00')   # 18%
        assert invoice.total_amount == Decimal('118000.00')
        assert invoice.cgst_amount == Decimal('0.00')
        assert invoice.sgst_amount == Decimal('0.00')

    def test_interstate_vs_intrastate(self, invoice):
        """Intrastate should split GST into CGST + SGST."""
        invoice.is_interstate = False
        invoice.cgst_percent = Decimal('9.00')
        invoice.sgst_percent = Decimal('9.00')
        invoice.igst_percent = Decimal('0.00')
        invoice.save()

        from apps.invoices.models import InvoiceItem
        InvoiceItem.objects.create(
            invoice=invoice,
            description='Local Haulage',
            quantity=Decimal('1'),
            unit='trip',
            unit_price=Decimal('10000.00'),
            amount=Decimal('10000.00'),
        )
        invoice.refresh_from_db()
        assert invoice.cgst_amount == Decimal('900.00')
        assert invoice.sgst_amount == Decimal('900.00')
        assert invoice.igst_amount == Decimal('0.00')
        assert invoice.total_gst   == Decimal('1800.00')

    def test_issue_invoice(self, auth_client, invoice):
        resp = auth_client.post(f'/api/v1/invoices/{invoice.id}/issue/')
        assert resp.status_code == status.HTTP_200_OK
        invoice.refresh_from_db()
        assert invoice.status == 'issued'

    def test_cannot_issue_non_draft(self, auth_client, invoice):
        invoice.status = 'issued'
        invoice.save()
        resp = auth_client.post(f'/api/v1/invoices/{invoice.id}/issue/')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_balance_due_updates(self, invoice):
        from apps.invoices.models import InvoiceItem
        InvoiceItem.objects.create(
            invoice=invoice, description='Freight',
            quantity=1, unit_price=Decimal('50000.00'), amount=Decimal('50000.00')
        )
        invoice.refresh_from_db()
        assert invoice.balance_due == invoice.total_amount


# =============================================================================
# PAYMENT TESTS
# =============================================================================

@pytest.mark.django_db
class TestPayments:

    def _setup_invoice_with_items(self, invoice):
        from apps.invoices.models import InvoiceItem
        InvoiceItem.objects.create(
            invoice=invoice, description='Ocean Freight',
            quantity=1, unit_price=Decimal('100000.00'), amount=Decimal('100000.00')
        )
        invoice.refresh_from_db()
        invoice.status = 'issued'
        invoice.save()
        return invoice

    def test_record_payment(self, auth_client, customer, invoice):
        invoice = self._setup_invoice_with_items(invoice)
        resp = auth_client.post('/api/v1/payments/', {
            'customer':       customer.id,
            'invoice':        invoice.id,
            'amount':         '50000.00',
            'currency':       'INR',
            'payment_method': 'bank_transfer',
            'payment_date':   str(date.today()),
            'reference_number': 'UTR123456789',
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['payment_number'].startswith('PAY')

    def test_payment_exceeds_balance(self, auth_client, customer, invoice):
        invoice = self._setup_invoice_with_items(invoice)
        resp = auth_client.post('/api/v1/payments/', {
            'customer':       customer.id,
            'invoice':        invoice.id,
            'amount':         str(float(invoice.total_amount) + 1),
            'payment_method': 'bank_transfer',
            'payment_date':   str(date.today()),
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_confirm_payment_updates_invoice(self, auth_client, customer, invoice, admin_user):
        invoice = self._setup_invoice_with_items(invoice)
        from apps.payments.models import Payment
        payment = Payment.objects.create(
            customer=customer,
            invoice=invoice,
            amount=invoice.total_amount,
            payment_method='bank_transfer',
            payment_date=date.today(),
            created_by=admin_user,
            updated_by=admin_user,
        )
        resp = auth_client.post(f'/api/v1/payments/{payment.id}/confirm/')
        assert resp.status_code == status.HTTP_200_OK
        invoice.refresh_from_db()
        assert invoice.status == 'paid'
        assert invoice.balance_due == Decimal('0.00')


# =============================================================================
# REPORTING TESTS
# =============================================================================

@pytest.mark.django_db
class TestReporting:

    def test_dashboard(self, auth_client, shipment):
        resp = auth_client.get('/api/v1/reports/dashboard/')
        assert resp.status_code == status.HTTP_200_OK
        assert 'shipments' in resp.data
        assert 'invoicing' in resp.data

    def test_revenue_report(self, auth_client, shipment):
        resp = auth_client.get('/api/v1/reports/revenue/')
        assert resp.status_code == status.HTTP_200_OK
        assert 'breakdown' in resp.data
        assert 'totals' in resp.data

    def test_shipment_profit_report(self, auth_client, shipment):
        resp = auth_client.get('/api/v1/reports/shipment-profit/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['count'] >= 1
        row = resp.data['results'][0]
        assert 'gross_profit' in row
        assert 'margin_pct' in row

    def test_cash_flow_report(self, auth_client):
        resp = auth_client.get('/api/v1/reports/cash-flow/')
        assert resp.status_code == status.HTTP_200_OK
        assert 'summary' in resp.data

    def test_report_date_filter(self, auth_client, shipment):
        resp = auth_client.get(
            f'/api/v1/reports/revenue/'
            f'?from_date={date.today()}&to_date={date.today()}'
        )
        assert resp.status_code == status.HTTP_200_OK


# =============================================================================
# ACCOUNTS TESTS
# =============================================================================

@pytest.mark.django_db
class TestAccounts:

    def test_ar_summary(self, auth_client):
        resp = auth_client.get('/api/v1/accounts/receivable/summary/')
        assert resp.status_code == status.HTTP_200_OK
        assert 'total_outstanding' in resp.data

    def test_ar_aging(self, auth_client):
        resp = auth_client.get('/api/v1/accounts/receivable/aging/')
        assert resp.status_code == status.HTTP_200_OK
        assert '0_30' in resp.data
        assert '90_plus' in resp.data

    def test_ap_summary(self, auth_client):
        resp = auth_client.get('/api/v1/accounts/payable/summary/')
        assert resp.status_code == status.HTTP_200_OK
        assert 'total_payable' in resp.data
