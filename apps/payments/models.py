"""
apps/payments/models.py
Payment tracking with partial payments, reconciliation, and transactions.
"""

from decimal import Decimal
from django.db import models
from django.db import transaction as db_transaction
from freight_project.base_model import AuditedModel


class Payment(AuditedModel):

    class Method(models.TextChoices):
        BANK_TRANSFER = 'bank_transfer', 'Bank Transfer (NEFT/RTGS/IMPS)'
        CHEQUE        = 'cheque',        'Cheque'
        CASH          = 'cash',          'Cash'
        UPI           = 'upi',           'UPI'
        CARD          = 'card',          'Card'
        ONLINE        = 'online',        'Online Gateway'
        LETTER_OF_CREDIT = 'lc',        'Letter of Credit'

    class Status(models.TextChoices):
        PENDING    = 'pending',    'Pending'
        CONFIRMED  = 'confirmed',  'Confirmed'
        BOUNCED    = 'bounced',    'Bounced / Failed'
        REFUNDED   = 'refunded',   'Refunded'

    payment_number   = models.CharField(max_length=30, unique=True, blank=True)
    customer         = models.ForeignKey('customers.Customer', on_delete=models.PROTECT,
                                         related_name='payments')
    invoice          = models.ForeignKey('invoices.Invoice', on_delete=models.PROTECT,
                                         related_name='payments')
    amount           = models.DecimalField(max_digits=14, decimal_places=2)
    currency         = models.CharField(max_length=5, default='INR')
    exchange_rate    = models.DecimalField(max_digits=10, decimal_places=4, default=1.0)
    payment_method   = models.CharField(max_length=20, choices=Method.choices)
    reference_number = models.CharField(max_length=100, blank=True,
                                        help_text='UTR / cheque number / gateway ref')
    payment_date     = models.DateField()
    bank_account     = models.CharField(max_length=100, blank=True)
    notes            = models.TextField(blank=True)
    status           = models.CharField(max_length=15, choices=Status.choices,
                                        default=Status.PENDING, db_index=True)
    reconciled       = models.BooleanField(default=False)
    reconciled_by    = models.ForeignKey(
        'users.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='+'
    )
    reconciled_at    = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.payment_number} – {self.customer.company_name} – {self.amount}"

    def confirm(self):
        """
        Atomically mark payment as confirmed and update invoice balance.
        """
        with db_transaction.atomic():
            self.status = Payment.Status.CONFIRMED
            self.save(update_fields=['status'])
            invoice = self.invoice
            invoice.amount_paid = (
                Payment.objects.filter(
                    invoice=invoice, status=Payment.Status.CONFIRMED
                ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
            )
            invoice.balance_due = invoice.total_amount - invoice.amount_paid
            invoice.save(update_fields=['amount_paid', 'balance_due'])
            invoice.update_payment_status()

            # Update customer outstanding balance
            customer = self.customer
            customer.outstanding_balance = (
                customer.invoices.exclude(
                    status__in=['paid', 'cancelled']
                ).aggregate(total=models.Sum('balance_due'))['total'] or Decimal('0.00')
            )
            customer.save(update_fields=['outstanding_balance'])

    def save(self, *args, **kwargs):
        if not self.payment_number:
            self.payment_number = self._generate_number()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_number():
        import datetime, random
        return f"PAY{datetime.date.today().strftime('%Y%m')}{random.randint(10000, 99999)}"

    class Meta:
        db_table  = 'payments'
        ordering  = ['-payment_date']
        indexes   = [
            models.Index(fields=['customer']),
            models.Index(fields=['invoice']),
            models.Index(fields=['status']),
            models.Index(fields=['payment_date']),
        ]


class Transaction(models.Model):
    """
    Double-entry bookkeeping record generated automatically per payment.
    Provides an audit trail for reconciliation and accounts.
    """

    class TxType(models.TextChoices):
        DEBIT  = 'debit',  'Debit'
        CREDIT = 'credit', 'Credit'

    payment     = models.ForeignKey(Payment, on_delete=models.CASCADE,
                                    related_name='transactions')
    tx_type     = models.CharField(max_length=10, choices=TxType.choices)
    account     = models.CharField(max_length=80,
                                   help_text='Accounts Receivable / Bank / Cash …')
    amount      = models.DecimalField(max_digits=14, decimal_places=2)
    narration   = models.CharField(max_length=200, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'transactions'
