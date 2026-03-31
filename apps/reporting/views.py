"""
apps/reporting/views.py
Revenue reports, shipment profit analysis, cash flow, and KPI dashboard.
All reports support ?from_date=YYYY-MM-DD&to_date=YYYY-MM-DD query params.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum, Count, Avg, Q, F
from django.db.models.functions import TruncMonth, TruncQuarter
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.invoices.models import Invoice
from apps.payments.models import Payment
from apps.shipments.models import Shipment
from apps.vendors.models import VendorPayment
from apps.users.permissions import IsFinanceTeam, IsAdminOrManager


# ── Date range helper ─────────────────────────────────────────────────────────
def _date_range(request):
    today = date.today()
    from_date = request.query_params.get('from_date')
    to_date   = request.query_params.get('to_date')
    try:
        from_date = date.fromisoformat(from_date) if from_date else today.replace(month=1, day=1)
        to_date   = date.fromisoformat(to_date)   if to_date   else today
    except ValueError:
        from_date = today.replace(month=1, day=1)
        to_date   = today
    return from_date, to_date


# ── KPI Dashboard ─────────────────────────────────────────────────────────────
class KPIDashboardView(APIView):
    """
    GET /api/v1/reports/dashboard/
    Top-level KPIs for the home screen.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from_date, to_date = _date_range(request)

        shipment_agg = Shipment.objects.filter(
            created_at__date__gte=from_date,
            created_at__date__lte=to_date,
        ).aggregate(
            total_shipments   = Count('id'),
            total_revenue     = Sum('selling_amount'),
            total_cost        = Sum('buying_amount'),
            active_shipments  = Count('id', filter=Q(
                status__in=[Shipment.Status.IN_TRANSIT, Shipment.Status.ON_VESSEL,
                            Shipment.Status.AT_ORIGIN_PORT, Shipment.Status.AT_DEST_PORT]
            )),
        )
        total_revenue = shipment_agg['total_revenue'] or Decimal('0')
        total_cost    = shipment_agg['total_cost']    or Decimal('0')
        gross_profit  = total_revenue - total_cost

        invoice_agg = Invoice.objects.filter(
            invoice_date__gte=from_date,
            invoice_date__lte=to_date,
        ).exclude(status=Invoice.Status.CANCELLED).aggregate(
            invoiced       = Sum('total_amount'),
            collected      = Sum('amount_paid'),
            outstanding    = Sum('balance_due'),
        )

        payment_agg = Payment.objects.filter(
            status=Payment.Status.CONFIRMED,
            payment_date__gte=from_date,
            payment_date__lte=to_date,
        ).aggregate(total_collected=Sum('amount'))

        return Response({
            'period': {'from': str(from_date), 'to': str(to_date)},
            'shipments': {
                'total':  shipment_agg['total_shipments']  or 0,
                'active': shipment_agg['active_shipments'] or 0,
                'revenue': float(total_revenue),
                'cost':   float(total_cost),
                'gross_profit': float(gross_profit),
                'profit_margin': round(float(gross_profit / total_revenue * 100), 2)
                                 if total_revenue else 0,
            },
            'invoicing': {
                'total_invoiced':  float(invoice_agg['invoiced']    or 0),
                'total_collected': float(invoice_agg['collected']   or 0),
                'outstanding':     float(invoice_agg['outstanding'] or 0),
            },
            'cash_collected': float(payment_agg['total_collected'] or 0),
        })


# ── Revenue Report ─────────────────────────────────────────────────────────────
class RevenueReportView(APIView):
    """
    GET /api/v1/reports/revenue/
    Monthly revenue, cost, and gross profit breakdown.
    """
    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get(self, request):
        from_date, to_date = _date_range(request)
        group_by = request.query_params.get('group_by', 'month')  # month | quarter

        trunc_fn = TruncQuarter if group_by == 'quarter' else TruncMonth

        rows = (
            Shipment.objects.filter(
                created_at__date__gte=from_date,
                created_at__date__lte=to_date,
            )
            .annotate(period=trunc_fn('created_at'))
            .values('period')
            .annotate(
                shipment_count = Count('id'),
                total_revenue  = Sum('selling_amount'),
                total_cost     = Sum('buying_amount'),
            )
            .order_by('period')
        )

        data = [
            {
                'period':         r['period'].strftime('%Y-%m') if r['period'] else None,
                'shipment_count': r['shipment_count'],
                'revenue':        float(r['total_revenue'] or 0),
                'cost':           float(r['total_cost']    or 0),
                'gross_profit':   float((r['total_revenue'] or 0) - (r['total_cost'] or 0)),
                'margin_pct':     round(
                    float(((r['total_revenue'] or 0) - (r['total_cost'] or 0))
                          / (r['total_revenue'] or 1) * 100), 2
                ),
            }
            for r in rows
        ]

        totals = {
            'revenue':      sum(r['revenue']      for r in data),
            'cost':         sum(r['cost']         for r in data),
            'gross_profit': sum(r['gross_profit'] for r in data),
            'shipments':    sum(r['shipment_count'] for r in data),
        }

        return Response({'period': {'from': str(from_date), 'to': str(to_date)},
                         'totals': totals, 'breakdown': data})


# ── Shipment Profit Report ────────────────────────────────────────────────────
class ShipmentProfitReportView(APIView):
    """
    GET /api/v1/reports/shipment-profit/
    Per-shipment profit & loss statement.
    """
    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get(self, request):
        from_date, to_date = _date_range(request)

        shipments = (
            Shipment.objects
            .filter(created_at__date__gte=from_date, created_at__date__lte=to_date)
            .select_related('customer', 'vendor')
            .order_by('-created_at')
        )

        data = [
            {
                'shipment_number':  s.shipment_number,
                'customer':         s.customer.company_name,
                'mode':             s.mode,
                'origin':           s.origin,
                'destination':      s.destination,
                'status':           s.status,
                'revenue':          float(s.selling_amount),
                'cost':             float(s.buying_amount),
                'gross_profit':     float(s.profit),
                'margin_pct':       float(s.profit_margin),
                'created_at':       str(s.created_at.date()),
            }
            for s in shipments
        ]

        return Response({
            'period':  {'from': str(from_date), 'to': str(to_date)},
            'count':   len(data),
            'results': data,
        })


# ── Cash Flow Report ──────────────────────────────────────────────────────────
class CashFlowReportView(APIView):
    """
    GET /api/v1/reports/cash-flow/
    Monthly cash inflow (customer payments) vs outflow (vendor payments).
    """
    permission_classes = [IsAuthenticated, IsFinanceTeam]

    def get(self, request):
        from_date, to_date = _date_range(request)

        inflow = (
            Payment.objects
            .filter(status=Payment.Status.CONFIRMED,
                    payment_date__gte=from_date, payment_date__lte=to_date)
            .annotate(month=TruncMonth('payment_date'))
            .values('month')
            .annotate(amount=Sum('amount'))
            .order_by('month')
        )

        outflow = (
            VendorPayment.objects
            .filter(status=VendorPayment.Status.PAID,
                    payment_date__gte=from_date, payment_date__lte=to_date)
            .annotate(month=TruncMonth('payment_date'))
            .values('month')
            .annotate(amount=Sum('amount'))
            .order_by('month')
        )

        inflow_map  = {r['month'].strftime('%Y-%m'): float(r['amount']) for r in inflow}
        outflow_map = {r['month'].strftime('%Y-%m'): float(r['amount']) for r in outflow}
        all_months  = sorted(set(inflow_map) | set(outflow_map))

        cash_flow = [
            {
                'month':   m,
                'inflow':  inflow_map.get(m,  0),
                'outflow': outflow_map.get(m, 0),
                'net':     round(inflow_map.get(m, 0) - outflow_map.get(m, 0), 2),
            }
            for m in all_months
        ]

        return Response({
            'period':   {'from': str(from_date), 'to': str(to_date)},
            'summary': {
                'total_inflow':  sum(r['inflow']  for r in cash_flow),
                'total_outflow': sum(r['outflow'] for r in cash_flow),
                'net_cash_flow': sum(r['net']     for r in cash_flow),
            },
            'monthly': cash_flow,
        })


# ── Customer Revenue Report ───────────────────────────────────────────────────
class CustomerRevenueReportView(APIView):
    """
    GET /api/v1/reports/customer-revenue/
    Revenue contribution by customer, sorted by total revenue desc.
    """
    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get(self, request):
        from_date, to_date = _date_range(request)

        rows = (
            Shipment.objects
            .filter(created_at__date__gte=from_date, created_at__date__lte=to_date)
            .values('customer__id', 'customer__company_name')
            .annotate(
                shipments     = Count('id'),
                total_revenue = Sum('selling_amount'),
                total_cost    = Sum('buying_amount'),
            )
            .order_by('-total_revenue')
        )

        data = [
            {
                'customer_id':   r['customer__id'],
                'customer':      r['customer__company_name'],
                'shipments':     r['shipments'],
                'revenue':       float(r['total_revenue'] or 0),
                'cost':          float(r['total_cost']    or 0),
                'gross_profit':  float((r['total_revenue'] or 0) - (r['total_cost'] or 0)),
            }
            for r in rows
        ]

        return Response({
            'period':  {'from': str(from_date), 'to': str(to_date)},
            'count':   len(data),
            'results': data,
        })
