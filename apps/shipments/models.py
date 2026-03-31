"""
apps/shipments/models.py
Shipment lifecycle + Container tracking.
"""

from django.db import models
from freight_project.base_model import AuditedModel


class Shipment(AuditedModel):

    class Mode(models.TextChoices):
        SEA_FCL    = 'sea_fcl',    'Sea – FCL'
        SEA_LCL    = 'sea_lcl',    'Sea – LCL'
        AIR        = 'air',        'Air'
        ROAD       = 'road',       'Road'
        RAIL       = 'rail',       'Rail'
        MULTIMODAL = 'multimodal', 'Multimodal'

    class Status(models.TextChoices):
        BOOKED         = 'booked',          'Booked'
        CARGO_RECEIVED = 'cargo_received',  'Cargo Received'
        IN_TRANSIT     = 'in_transit',      'In Transit'
        AT_ORIGIN_PORT = 'at_origin_port',  'At Origin Port'
        ON_VESSEL      = 'on_vessel',       'On Vessel'
        AT_DEST_PORT   = 'at_dest_port',    'At Destination Port'
        CUSTOMS_HOLD   = 'customs_hold',    'Customs Hold'
        OUT_FOR_DEL    = 'out_for_delivery','Out for Delivery'
        DELIVERED      = 'delivered',       'Delivered'
        CANCELLED      = 'cancelled',       'Cancelled'

    shipment_number = models.CharField(max_length=30, unique=True, blank=True)
    quotation       = models.OneToOneField(
        'quotations.Quotation', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='shipment',
    )
    customer        = models.ForeignKey(
        'customers.Customer', on_delete=models.PROTECT, related_name='shipments'
    )
    vendor          = models.ForeignKey(
        'vendors.Vendor', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='shipments',
    )

    # Route
    mode            = models.CharField(max_length=15, choices=Mode.choices)
    origin          = models.CharField(max_length=150)
    destination     = models.CharField(max_length=150)
    port_of_loading = models.CharField(max_length=150, blank=True)
    port_of_discharge = models.CharField(max_length=150, blank=True)

    # Vessel / Carrier
    carrier_name    = models.CharField(max_length=100, blank=True)
    vessel_name     = models.CharField(max_length=100, blank=True)
    voyage_number   = models.CharField(max_length=50, blank=True)
    mbl_number      = models.CharField(max_length=50, blank=True,
                                       help_text='Master Bill of Lading')
    hbl_number      = models.CharField(max_length=50, blank=True,
                                       help_text='House Bill of Lading')
    awb_number      = models.CharField(max_length=50, blank=True,
                                       help_text='Airway Bill (air shipments)')

    # Dates
    etd             = models.DateField(null=True, blank=True,
                                       help_text='Estimated Time of Departure')
    eta             = models.DateField(null=True, blank=True,
                                       help_text='Estimated Time of Arrival')
    atd             = models.DateField(null=True, blank=True,
                                       help_text='Actual Time of Departure')
    ata             = models.DateField(null=True, blank=True,
                                       help_text='Actual Time of Arrival')

    # Financials
    currency        = models.CharField(max_length=5, default='INR')
    selling_amount  = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    buying_amount   = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    status          = models.CharField(max_length=25, choices=Status.choices,
                                       default=Status.BOOKED, db_index=True)
    notes           = models.TextField(blank=True)

    def __str__(self):
        return f"{self.shipment_number} – {self.customer.company_name}"

    @property
    def profit(self):
        return self.selling_amount - self.buying_amount

    @property
    def profit_margin(self):
        if self.selling_amount:
            return round((self.profit / self.selling_amount) * 100, 2)
        return 0

    def save(self, *args, **kwargs):
        if not self.shipment_number:
            self.shipment_number = self._generate_number()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_number():
        import datetime, random
        prefix = datetime.date.today().strftime('SHP%Y%m')
        return f"{prefix}{random.randint(1000, 9999)}"

    class Meta:
        db_table  = 'shipments'
        ordering  = ['-created_at']
        indexes   = [
            models.Index(fields=['customer']),
            models.Index(fields=['status']),
            models.Index(fields=['shipment_number']),
            models.Index(fields=['eta']),
        ]


class Container(models.Model):

    class ContainerType(models.TextChoices):
        DRY_20   = '20GP', '20\' General Purpose'
        DRY_40   = '40GP', '40\' General Purpose'
        HC_40    = '40HC', '40\' High Cube'
        REEFER_20 = '20RF', '20\' Reefer'
        REEFER_40 = '40RF', '40\' Reefer'
        OOG      = 'OOG',  'Out of Gauge'
        TANK     = 'TANK', 'Tank Container'

    shipment       = models.ForeignKey(Shipment, on_delete=models.CASCADE,
                                       related_name='containers')
    container_number = models.CharField(max_length=15, blank=True)
    container_type = models.CharField(max_length=10, choices=ContainerType.choices)
    seal_number    = models.CharField(max_length=30, blank=True)
    gross_weight   = models.DecimalField(max_digits=10, decimal_places=3,
                                         null=True, blank=True,
                                         help_text='kg')
    cbm            = models.DecimalField(max_digits=10, decimal_places=3,
                                         null=True, blank=True)
    packages       = models.PositiveIntegerField(default=0)
    description    = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.container_number or 'TBD'} ({self.container_type})"

    class Meta:
        db_table = 'containers'


class ShipmentTracking(models.Model):
    """Immutable event log for a shipment — one row per status change."""

    shipment    = models.ForeignKey(Shipment, on_delete=models.CASCADE,
                                    related_name='tracking_events')
    status      = models.CharField(max_length=25)
    location    = models.CharField(max_length=150, blank=True)
    description = models.TextField(blank=True)
    event_date  = models.DateTimeField()
    recorded_by = models.ForeignKey(
        'users.User', null=True, on_delete=models.SET_NULL, related_name='+'
    )
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'shipment_tracking'
        ordering = ['-event_date']
