"""
apps/vendors/models.py
Vendor + VendorRate + VendorPayment
"""

from django.db import models
from freight_project.base_model import AuditedModel


class Vendor(AuditedModel):

    class ServiceType(models.TextChoices):
        SHIPPING_LINE = 'shipping_line',    'Shipping Line'
        AIRLINE       = 'airline',          'Airline'
        TRUCKING      = 'trucking',         'Trucking / Road'
        CFS           = 'cfs',              'CFS / ICD'
        CUSTOMS       = 'customs_broker',   'Customs Broker'
        SURVEYOR      = 'surveyor',         'Surveyor'
        WAREHOUSE     = 'warehouse',        'Warehouse'
        OTHER         = 'other',            'Other'

    class Status(models.TextChoices):
        ACTIVE   = 'active',   'Active'
        INACTIVE = 'inactive', 'Inactive'
        BLOCKED  = 'blocked',  'Blocked'

    name          = models.CharField(max_length=200)
    service_type  = models.CharField(max_length=20, choices=ServiceType.choices)
    gst           = models.CharField(max_length=20, blank=True, null=True, unique=True)
    pan           = models.CharField(max_length=12, blank=True)
    contact_name  = models.CharField(max_length=100, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    address       = models.TextField(blank=True)
    bank_name     = models.CharField(max_length=100, blank=True)
    bank_account  = models.CharField(max_length=30, blank=True)
    bank_ifsc     = models.CharField(max_length=15, blank=True)
    credit_limit  = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    credit_days   = models.PositiveSmallIntegerField(default=30)
    status        = models.CharField(max_length=15, choices=Status.choices,
                                     default=Status.ACTIVE)
    notes         = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.service_type})"

    class Meta:
        db_table = 'vendors'
        ordering = ['name']
        indexes  = [models.Index(fields=['service_type', 'status'])]


class VendorRate(models.Model):
    """Rate card for a vendor on a specific lane/service."""

    vendor        = models.ForeignKey(Vendor, on_delete=models.CASCADE,
                                      related_name='rates')
    service_desc  = models.CharField(max_length=200)
    origin        = models.CharField(max_length=150, blank=True)
    destination   = models.CharField(max_length=150, blank=True)
    mode          = models.CharField(max_length=20, blank=True)
    rate          = models.DecimalField(max_digits=12, decimal_places=2)
    currency      = models.CharField(max_length=5, default='INR')
    unit          = models.CharField(max_length=30, blank=True,
                                     help_text='per container / per kg / per CBM …')
    valid_from    = models.DateField()
    valid_to      = models.DateField(null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.vendor.name} – {self.service_desc} – {self.rate} {self.currency}"

    class Meta:
        db_table = 'vendor_rates'


class VendorPayment(AuditedModel):

    class Status(models.TextChoices):
        PENDING   = 'pending',   'Pending'
        APPROVED  = 'approved',  'Approved'
        PAID      = 'paid',      'Paid'
        CANCELLED = 'cancelled', 'Cancelled'

    payment_number   = models.CharField(max_length=30, unique=True, blank=True)
    vendor           = models.ForeignKey(Vendor, on_delete=models.PROTECT,
                                         related_name='payments')
    shipment         = models.ForeignKey(
        'shipments.Shipment', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='vendor_payments',
    )
    amount           = models.DecimalField(max_digits=14, decimal_places=2)
    currency         = models.CharField(max_length=5, default='INR')
    payment_method   = models.CharField(max_length=30, blank=True)
    reference_number = models.CharField(max_length=100, blank=True)
    payment_date     = models.DateField(null=True, blank=True)
    due_date         = models.DateField(null=True, blank=True)
    description      = models.CharField(max_length=200, blank=True)
    status           = models.CharField(max_length=15, choices=Status.choices,
                                        default=Status.PENDING)

    def save(self, *args, **kwargs):
        if not self.payment_number:
            import datetime, random
            self.payment_number = (
                f"VP{datetime.date.today().strftime('%Y%m')}{random.randint(10000,99999)}"
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.payment_number} – {self.vendor.name} – {self.amount}"

    class Meta:
        db_table = 'vendor_payments'
        ordering = ['-created_at']
