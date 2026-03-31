"""
apps/invoices/models.py
Invoice + InvoiceItem with GST calculation and multi-currency support.
"""

from decimal import Decimal
from django.db import models
from django.conf import settings
from freight_project.base_model import AuditedModel


class Invoice(AuditedModel):

    class Status(models.TextChoices):
        DRAFT     = 'draft',     'Draft'
        ISSUED    = 'issued',    'Issued'
        SENT      = 'sent',      'Sent'
        PARTIAL   = 'partial',   'Partially Paid'
        PAID      = 'paid',      'Paid'
        OVERDUE   = 'overdue',   'Overdue'
        CANCELLED = 'cancelled', 'Cancelled'

    class InvoiceType(models.TextChoices):
        TAX_INVOICE    = 'tax_invoice',    'Tax Invoice'
        PROFORMA       = 'proforma',       'Proforma Invoice'
        CREDIT_NOTE    = 'credit_note',    'Credit Note'
        DEBIT_NOTE     = 'debit_note',     'Debit Note'

    invoice_number = models.CharField(max_length=30, unique=True, blank=True)
    invoice_type   = models.CharField(max_length=20, choices=InvoiceType.choices,
                                      default=InvoiceType.TAX_INVOICE)
    customer       = models.ForeignKey('customers.Customer', on_delete=models.PROTECT,
                                       related_name='invoices')
    shipment       = models.OneToOneField('shipments.Shipment', null=True, blank=True,
                                          on_delete=models.SET_NULL, related_name='invoice')
    invoice_date   = models.DateField(auto_now_add=True)
    due_date       = models.DateField(null=True, blank=True)

    # Financials
    currency       = models.CharField(max_length=5, default='INR')
    exchange_rate  = models.DecimalField(max_digits=10, decimal_places=4, default=1.0)
    subtotal       = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # GST breakdown (IGST or CGST+SGST depending on supply type)
    igst_percent   = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    igst_amount    = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cgst_percent   = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    cgst_amount    = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    sgst_percent   = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    sgst_amount    = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_gst      = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    total_amount   = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    amount_paid    = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    balance_due    = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    status         = models.CharField(max_length=15, choices=Status.choices,
                                      default=Status.DRAFT, db_index=True)
    notes          = models.TextField(blank=True)
    terms          = models.TextField(blank=True)
    pdf_url        = models.TextField(blank=True)

    # GST supply type
    is_interstate  = models.BooleanField(default=True,
                                         help_text='True=IGST, False=CGST+SGST')

    def __str__(self):
        return f"{self.invoice_number} – {self.customer.company_name}"

    def recalculate(self):
        """Recompute all totals from line items."""
        items = self.items.all()
        self.subtotal = sum(item.amount for item in items)
        taxable       = self.subtotal - self.discount_amount

        if self.is_interstate:
            self.igst_amount = (taxable * self.igst_percent / 100).quantize(Decimal('0.01'))
            self.cgst_amount = Decimal('0.00')
            self.sgst_amount = Decimal('0.00')
        else:
            self.igst_amount = Decimal('0.00')
            self.cgst_amount = (taxable * self.cgst_percent / 100).quantize(Decimal('0.01'))
            self.sgst_amount = (taxable * self.sgst_percent / 100).quantize(Decimal('0.01'))

        self.total_gst    = self.igst_amount + self.cgst_amount + self.sgst_amount
        self.total_amount = taxable + self.total_gst
        self.balance_due  = self.total_amount - self.amount_paid
        self.save(update_fields=[
            'subtotal', 'igst_amount', 'cgst_amount', 'sgst_amount',
            'total_gst', 'total_amount', 'balance_due',
        ])

    def update_payment_status(self):
        """Called by payment module after recording a payment."""
        if self.balance_due <= 0:
            self.status = Invoice.Status.PAID
        elif self.amount_paid > 0:
            self.status = Invoice.Status.PARTIAL
        self.save(update_fields=['status'])

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = self._generate_number()
        self.balance_due = self.total_amount - self.amount_paid
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_number():
        import datetime, random
        prefix = datetime.date.today().strftime('INV%Y%m')
        return f"{prefix}{random.randint(10000, 99999)}"

    class Meta:
        db_table  = 'invoices'
        ordering  = ['-invoice_date']
        indexes   = [
            models.Index(fields=['customer']),
            models.Index(fields=['status']),
            models.Index(fields=['invoice_number']),
            models.Index(fields=['due_date']),
        ]


class InvoiceItem(models.Model):
    invoice     = models.ForeignKey(Invoice, on_delete=models.CASCADE,
                                    related_name='items')
    description = models.CharField(max_length=200)
    hsn_sac     = models.CharField(max_length=10, blank=True,
                                    help_text='HSN / SAC code for GST')
    quantity    = models.DecimalField(max_digits=10, decimal_places=3, default=1)
    unit        = models.CharField(max_length=20, blank=True)
    unit_price  = models.DecimalField(max_digits=12, decimal_places=2)
    amount      = models.DecimalField(max_digits=14, decimal_places=2)

    def save(self, *args, **kwargs):
        self.amount = self.quantity * self.unit_price
        super().save(*args, **kwargs)
        self.invoice.recalculate()

    def delete(self, *args, **kwargs):
        invoice = self.invoice
        super().delete(*args, **kwargs)
        invoice.recalculate()

    class Meta:
        db_table = 'invoice_items'
