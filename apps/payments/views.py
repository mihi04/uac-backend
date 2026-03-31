"""
apps/payments/views.py
"""

from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Payment, Transaction
from .serializers import (
    PaymentListSerializer, PaymentDetailSerializer, PaymentWriteSerializer,
)
from apps.users.permissions import IsFinanceTeam


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related(
        'customer', 'invoice'
    ).prefetch_related('transactions')
    permission_classes = [IsAuthenticated, IsFinanceTeam]
    search_fields = ['payment_number', 'customer__company_name',
                     'invoice__invoice_number', 'reference_number']
    ordering_fields = ['payment_date', 'amount', 'status']
    ordering = ['-payment_date']

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return PaymentWriteSerializer
        if self.action == 'retrieve':
            return PaymentDetailSerializer
        return PaymentListSerializer

    def perform_create(self, serializer):
        payment = serializer.save(
            created_by=self.request.user,
            updated_by=self.request.user,
        )
        # Auto-create double-entry transactions
        Transaction.objects.bulk_create([
            Transaction(
                payment=payment,
                tx_type=Transaction.TxType.DEBIT,
                account='Bank / Cash',
                amount=payment.amount,
                narration=f"Payment received – {payment.payment_number}",
            ),
            Transaction(
                payment=payment,
                tx_type=Transaction.TxType.CREDIT,
                account='Accounts Receivable',
                amount=payment.amount,
                narration=f"Invoice {payment.invoice.invoice_number} payment",
            ),
        ])

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=True, methods=['post'], url_path='confirm')
    def confirm(self, request, pk=None):
        payment = self.get_object()
        if payment.status != Payment.Status.PENDING:
            return Response({'detail': 'Only PENDING payments can be confirmed.'},
                            status=status.HTTP_400_BAD_REQUEST)
        payment.confirm()
        return Response({'detail': 'Payment confirmed and invoice updated.'})

    @action(detail=True, methods=['post'], url_path='reconcile')
    def reconcile(self, request, pk=None):
        payment = self.get_object()
        if payment.reconciled:
            return Response({'detail': 'Already reconciled.'})
        payment.reconciled    = True
        payment.reconciled_by = request.user
        payment.reconciled_at = timezone.now()
        payment.save(update_fields=['reconciled', 'reconciled_by', 'reconciled_at'])
        return Response({'detail': 'Payment reconciled.'})

    @action(detail=False, methods=['get'], url_path='unreconciled')
    def unreconciled(self, request):
        qs = self.get_queryset().filter(
            reconciled=False,
            status=Payment.Status.CONFIRMED,
        )
        serializer = PaymentListSerializer(qs, many=True)
        return Response({'count': qs.count(), 'results': serializer.data})
