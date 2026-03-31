"""
apps/accounts/views.py
Accounts Receivable + Accounts Payable dashboards.
No separate models needed — these are analytical views over
Invoice, Payment, and VendorPayment data.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum, Count, Q, F, ExpressionWrapper, DecimalField
from django.db.models.functions import TruncMonth
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.invoices.models import Invoice
from apps.payments.models import Payment
from apps.vendors.models import VendorPayment
from apps.users.permissions import IsFinanceTeam


# ── Helpers ───────────────────────────────────────────────────────────────────
def _aging_buckets(invoices_qs):
    """
    Classifies overdue invoices into aging buckets:
    0-30 | 31-60 | 61-90 | 90+ days.
    Returns list of dicts.
    """
    today = date.today()
    buckets = {'0_30': [], '31_60': [], '61_90': [], '90_plus': []}

    for inv in invoices_qs.filter(
        balance_due__gt=0,
        due_date__lt=today,
    ).select_related('customer'):
        days_overdue = (today - inv.due_date).days
        row = {
            'invoice_number': inv.invoice_number,
            'customer':       inv.customer.company_name,
            'due_date':       str(inv.due_date),
            'days_overdue':   days_overdue,
            'balance_due':    float(inv.balance_due),
            'currency':       inv.currency,
        }
        if days_overdue <= 30:
            buckets['0_30'].append(row)
        elif days_overdue <= 60:
            buckets['31_60'].append(row)
        elif days_overdue <= 90:
            buckets['61_90'].append(row)
        else:
            buckets['90_plus'].append(row)

    return {
        bucket: {
            'count':     len(items),
            'total':     round(sum(i['balance_due'] for i in items), 2),
            'invoices':  items,
        }
        for bucket, items in buckets.items()
    }


# ── Accounts Receivable ───────────────────────────────────────────────────────
class ReceivableSummaryView(APIView):
    """
    GET /api/v1/accounts/receivable/summary/
    High-level AR dashboard: outstanding, overdue, collected this month.
    """
    permission_classes = [IsAuthenticated, IsFinanceTeam]

    def get(self, request):
        today = date.today()
        month_start = today.replace(day=1)

        agg = Invoice.objects.exclude(
            status__in=[Invoice.Status.CANCELLED, Invoice.Status.DRAFT]
        ).aggregate(
            total_invoiced   = Sum('total_amount'),
            total_collected  = Sum('amount_paid'),
            total_outstanding= Sum('balance_due'),
            overdue_amount   = Sum(
                'balance_due',
                filter=Q(due_date__lt=today, balance_due__gt=0)
            ),
        )

        collected_this_month = Payment.objects.filter(
            status=Payment.Status.CONFIRMED,
            payment_date__gte=month_start,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        return Response({
            'total_invoiced':    float(agg['total_invoiced']    or 0),
            'total_collected':   float(agg['total_collected']   or 0),
            'total_outstanding': float(agg['total_outstanding'] or 0),
            'overdue_amount':    float(agg['overdue_amount']    or 0),
            'collected_this_month': float(collected_this_month),
        })


class ReceivableAgingView(APIView):
    """
    GET /api/v1/accounts/receivable/aging/
    Aging report broken into 0-30, 31-60, 61-90, 90+ day buckets.
    """
    permission_classes = [IsAuthenticated, IsFinanceTeam]

    def get(self, request):
        qs = Invoice.objects.exclude(
            status__in=[Invoice.Status.CANCELLED, Invoice.Status.DRAFT]
        )
        return Response(_aging_buckets(qs))


class OutstandingInvoicesView(APIView):
    """
    GET /api/v1/accounts/receivable/outstanding/
    All unpaid / partially paid invoices, sorted by due date.
    """
    permission_classes = [IsAuthenticated, IsFinanceTeam]

    def get(self, request):
        qs = Invoice.objects.filter(
            balance_due__gt=0,
        ).exclude(
            status__in=[Invoice.Status.CANCELLED, Invoice.Status.DRAFT]
        ).select_related('customer').order_by('due_date')

        data = [
            {
                'id':             inv.id,
                'invoice_number': inv.invoice_number,
                'customer':       inv.customer.company_name,
                'invoice_date':   str(inv.invoice_date),
                'due_date':       str(inv.due_date) if inv.due_date else None,
                'total_amount':   float(inv.total_amount),
                'amount_paid':    float(inv.amount_paid),
                'balance_due':    float(inv.balance_due),
                'currency':       inv.currency,
                'status':         inv.status,
                'days_overdue':   (date.today() - inv.due_date).days
                                  if inv.due_date and inv.due_date < date.today() else 0,
            }
            for inv in qs
        ]
        return Response({'count': len(data), 'results': data})


# ── Accounts Payable ──────────────────────────────────────────────────────────
class PayableSummaryView(APIView):
    """
    GET /api/v1/accounts/payable/summary/
    High-level AP dashboard: total payable, overdue, paid this month.
    """
    permission_classes = [IsAuthenticated, IsFinanceTeam]

    def get(self, request):
        today = date.today()
        month_start = today.replace(day=1)

        agg = VendorPayment.objects.exclude(
            status=VendorPayment.Status.CANCELLED
        ).aggregate(
            total_payable = Sum('amount', filter=~Q(status=VendorPayment.Status.PAID)),
            total_paid    = Sum('amount', filter=Q(status=VendorPayment.Status.PAID)),
            overdue       = Sum(
                'amount',
                filter=Q(due_date__lt=today, status=VendorPayment.Status.PENDING),
            ),
        )

        paid_this_month = VendorPayment.objects.filter(
            status=VendorPayment.Status.PAID,
            payment_date__gte=month_start,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        return Response({
            'total_payable':    float(agg['total_payable']  or 0),
            'total_paid':       float(agg['total_paid']     or 0),
            'overdue_payable':  float(agg['overdue']        or 0),
            'paid_this_month':  float(paid_this_month),
        })


class PendingPayablesView(APIView):
    """
    GET /api/v1/accounts/payable/pending/
    Vendor payments awaiting approval or processing.
    """
    permission_classes = [IsAuthenticated, IsFinanceTeam]

    def get(self, request):
        qs = VendorPayment.objects.filter(
            status__in=[VendorPayment.Status.PENDING, VendorPayment.Status.APPROVED]
        ).select_related('vendor', 'shipment').order_by('due_date')

        data = [
            {
                'id':              vp.id,
                'payment_number':  vp.payment_number,
                'vendor':          vp.vendor.name,
                'shipment_number': vp.shipment.shipment_number if vp.shipment else None,
                'amount':          float(vp.amount),
                'currency':        vp.currency,
                'due_date':        str(vp.due_date) if vp.due_date else None,
                'status':          vp.status,
                'description':     vp.description,
            }
            for vp in qs
        ]
        return Response({'count': len(data), 'results': data})
