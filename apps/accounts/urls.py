"""apps/accounts/urls.py"""
from django.urls import path
from .views import (
    ReceivableSummaryView, ReceivableAgingView, OutstandingInvoicesView,
    PayableSummaryView, PendingPayablesView,
)

urlpatterns = [
    # Receivable
    path('receivable/summary/',     ReceivableSummaryView.as_view(),  name='ar-summary'),
    path('receivable/aging/',       ReceivableAgingView.as_view(),    name='ar-aging'),
    path('receivable/outstanding/', OutstandingInvoicesView.as_view(),name='ar-outstanding'),
    # Payable
    path('payable/summary/',        PayableSummaryView.as_view(),     name='ap-summary'),
    path('payable/pending/',        PendingPayablesView.as_view(),    name='ap-pending'),
]
