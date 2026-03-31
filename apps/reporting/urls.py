"""apps/reporting/urls.py"""
from django.urls import path
from .views import (
    KPIDashboardView,
    RevenueReportView,
    ShipmentProfitReportView,
    CashFlowReportView,
    CustomerRevenueReportView,
)

urlpatterns = [
    path('dashboard/',        KPIDashboardView.as_view(),           name='report-dashboard'),
    path('revenue/',          RevenueReportView.as_view(),          name='report-revenue'),
    path('shipment-profit/',  ShipmentProfitReportView.as_view(),   name='report-shipment-profit'),
    path('cash-flow/',        CashFlowReportView.as_view(),         name='report-cash-flow'),
    path('customer-revenue/', CustomerRevenueReportView.as_view(),  name='report-customer-revenue'),
]
