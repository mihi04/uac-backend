"""
apps/quotations/models.py
Quotation + QuotationItem with auto-calculation logic.
"""

from django.db import models
from django.conf import settings
from freight_project.base_model import AuditedModel


class ChargeType(models.Model):
    """Master list of charge types: Ocean Freight, THC, Documentation, etc."""
    name        = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_taxable  = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'charge_types'
        ordering = ['name']


class Quotation(AuditedModel):

    class Mode(models.TextChoices):
        SEA_FCL = 'sea_fcl', 'Sea – FCL'
        SEA_LCL = 'sea_lcl', 'Sea – LCL'
        AIR     = 'air',     'Air'
        ROAD    = 'road',    'Road'
        RAIL    = 'rail',    'Rail'
        MULTIMODAL = 'multimodal', 'Multimodal'

    class Status(models.TextChoices):
        DRAFT     = 'draft',     'Draft'
        SENT      = 'sent',      'Sent to Customer'
        APPROVED  = 'approved',  'Approved'
        REJECTED  = 'rejected',  'Rejected'
        EXPIRED   = 'expired',   'Expired'
        CONVERTED = 'converted', 'Converted to Shipment'

    quotation_number = models.CharField(max_length=30, unique=True, blank=True)
    customer         = models.ForeignKey('customers.Customer', on_delete=models.PROTECT,
                                         related_name='quotations')
    origin           = models.CharField(max_length=150)
    destination      = models.CharField(max_length=150)
    mode             = models.CharField(max_length=15, choices=Mode.choices)
    incoterms        = models.CharField(max_length=10, blank=True,
                                        help_text='EXW, FOB, CIF, DDP …')
    cargo_type       = models.CharField(max_length=80, blank=True)
    cargo_ready_date = models.DateField(null=True, blank=True)
    delivery_date    = models.DateField(null=True, blank=True)
    validity_date    = models.DateField(null=True, blank=True)

    # Financial
    currency         = models.CharField(max_length=5, default='INR')
    exchange_rate    = models.DecimalField(max_digits=10, decimal_places=4, default=1.0)
    subtotal         = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    gst_percent      = models.DecimalField(max_digits=5, decimal_places=2,
                                           default=settings.DEFAULT_GST_PERCENT)
    gst_amount       = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_amount     = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    status           = models.CharField(max_length=15, choices=Status.choices,
                                        default=Status.DRAFT, db_index=True)
    notes            = models.TextField(blank=True)
    terms_conditions = models.TextField(blank=True)

    def __str__(self):
        return f"{self.quotation_number} – {self.customer.company_name}"

    def recalculate(self):
        """Recompute subtotal, GST, and total from line items."""
        self.subtotal    = sum(item.amount for item in self.items.all())
        self.gst_amount  = (self.subtotal * self.gst_percent / 100).quantize(
                            __import__('decimal').Decimal('0.01'))
        self.total_amount = self.subtotal + self.gst_amount
        self.save(update_fields=['subtotal', 'gst_amount', 'total_amount'])

    def save(self, *args, **kwargs):
        if not self.quotation_number:
            self.quotation_number = self._generate_number()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_number():
        import datetime, random
        prefix = datetime.date.today().strftime('QT%Y%m')
        suffix = str(random.randint(1000, 9999))
        return f"{prefix}{suffix}"

    class Meta:
        db_table  = 'quotations'
        ordering  = ['-created_at']
        indexes   = [
            models.Index(fields=['customer']),
            models.Index(fields=['status']),
            models.Index(fields=['quotation_number']),
        ]


class QuotationItem(models.Model):
    """One charge line within a Quotation."""

    quotation   = models.ForeignKey(Quotation, on_delete=models.CASCADE,
                                    related_name='items')
    charge_type = models.ForeignKey(ChargeType, on_delete=models.PROTECT,
                                    related_name='+')
    description = models.CharField(max_length=200, blank=True)
    quantity    = models.DecimalField(max_digits=10, decimal_places=3, default=1)
    unit        = models.CharField(max_length=20, blank=True,
                                   help_text='CBM, KG, container, lot …')
    unit_price  = models.DecimalField(max_digits=12, decimal_places=2)
    amount      = models.DecimalField(max_digits=14, decimal_places=2)

    def save(self, *args, **kwargs):
        self.amount = self.quantity * self.unit_price
        super().save(*args, **kwargs)
        self.quotation.recalculate()

    def delete(self, *args, **kwargs):
        quotation = self.quotation
        super().delete(*args, **kwargs)
        quotation.recalculate()

    def __str__(self):
        return f"{self.charge_type.name}: {self.amount}"

    class Meta:
        db_table = 'quotation_items'
