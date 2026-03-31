"""
apps/customers/models.py
Customer, CustomerContact, CustomerAddress, CustomerDocument
"""

from django.db import models
from freight_project.base_model import AuditedModel


class Customer(AuditedModel):

    class BusinessType(models.TextChoices):
        IMPORTER   = 'importer',   'Importer'
        EXPORTER   = 'exporter',   'Exporter'
        TRADER     = 'trader',     'Trader'
        MANUFACTURER = 'manufacturer', 'Manufacturer'
        FREIGHT_BROKER = 'freight_broker', 'Freight Broker'
        OTHER      = 'other',      'Other'

    class Status(models.TextChoices):
        ACTIVE     = 'active',   'Active'
        INACTIVE   = 'inactive', 'Inactive'
        BLOCKED    = 'blocked',  'Blocked'
        PROSPECT   = 'prospect', 'Prospect'

    class LegalStructure(models.TextChoices):
        PROPRIETORSHIP = 'proprietorship', 'Proprietorship'
        PARTNERSHIP    = 'partnership',    'Partnership'
        PVT_LTD        = 'pvt_ltd',        'Private Limited'
        LLP            = 'llp',            'LLP'
        OTHER          = 'other',          'Other'

    company_name   = models.CharField(max_length=200)
    business_type  = models.CharField(max_length=30, choices=BusinessType.choices,
                                      default=BusinessType.TRADER)
    legal_structure = models.CharField(
        max_length=20, choices=LegalStructure.choices, blank=True, null=True,
        help_text='Legal form of the entity (Companies Act / registration type)',
    )
    industry = models.CharField(max_length=120, blank=True,
                                help_text='Industry / nature of business description')
    company_registration_number = models.CharField(max_length=80, blank=True)
    msme_registration = models.CharField(max_length=40, blank=True)
    # KYC / Tax IDs
    gst            = models.CharField(max_length=20, blank=True, unique=True, null=True,
                                      help_text='15-char GST Identification Number')
    pan            = models.CharField(max_length=12, blank=True,
                                      help_text='10-char PAN')
    iec            = models.CharField(max_length=15, blank=True,
                                      help_text='Importer-Exporter Code')
    # Credit
    credit_limit   = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    credit_days    = models.PositiveSmallIntegerField(default=30,
                                                      help_text='Payment due in N days')
    outstanding_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    # Misc
    website        = models.URLField(blank=True)
    notes          = models.TextField(blank=True)
    bank_account_number = models.CharField(max_length=34, blank=True)
    bank_ifsc           = models.CharField(max_length=20, blank=True)
    bank_name           = models.CharField(max_length=120, blank=True)
    bank_branch         = models.CharField(max_length=120, blank=True)
    shipment_preferences = models.TextField(
        blank=True,
        help_text='Shipment type, trade routes, cargo types, typical volume',
    )
    terms_accepted = models.BooleanField(default=False)
    status         = models.CharField(max_length=15, choices=Status.choices,
                                      default=Status.ACTIVE, db_index=True)
    assigned_to    = models.ForeignKey(
        'users.User', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='assigned_customers',
    )

    def __str__(self):
        return self.company_name

    @property
    def available_credit(self):
        return self.credit_limit - self.outstanding_balance

    class Meta:
        db_table  = 'customers'
        ordering  = ['company_name']
        indexes   = [
            models.Index(fields=['gst']),
            models.Index(fields=['status']),
        ]


class CustomerContact(models.Model):
    customer    = models.ForeignKey(Customer, on_delete=models.CASCADE,
                                    related_name='contacts')
    name        = models.CharField(max_length=100)
    designation = models.CharField(max_length=80, blank=True)
    phone       = models.CharField(max_length=20, blank=True)
    email       = models.EmailField(blank=True)
    is_primary  = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.customer.company_name})"

    class Meta:
        db_table = 'customer_contacts'


class CustomerAddress(models.Model):

    class AddressType(models.TextChoices):
        REGISTERED = 'registered', 'Registered office'
        BILLING  = 'billing',  'Billing'
        SHIPPING = 'shipping', 'Shipping'
        BOTH     = 'both',     'Both'

    customer     = models.ForeignKey(Customer, on_delete=models.CASCADE,
                                     related_name='addresses')
    address_type = models.CharField(max_length=15, choices=AddressType.choices,
                                    default=AddressType.BOTH)
    address_line = models.TextField()
    city         = models.CharField(max_length=80)
    state        = models.CharField(max_length=80)
    country      = models.CharField(max_length=80, default='India')
    pin_code     = models.CharField(max_length=12)
    is_default   = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.address_type} – {self.city}"

    class Meta:
        db_table = 'customer_addresses'


class CustomerDocument(models.Model):

    class DocType(models.TextChoices):
        GST_CERT   = 'gst_certificate',    'GST Certificate'
        PAN_COPY   = 'pan_copy',           'PAN Copy'
        IEC_CERT   = 'iec_certificate',    'IEC Certificate'
        ADDRESS_PROOF = 'address_proof',   'Address proof'
        AUTH_SIGNATORY = 'authorized_signatory_id', 'Authorized signatory ID'
        TRADE_LIC  = 'trade_license',      'Trade License'
        BANK_STMT  = 'bank_statement',     'Bank Statement'
        OTHER      = 'other',              'Other'

    customer      = models.ForeignKey(Customer, on_delete=models.CASCADE,
                                      related_name='documents')
    document_type = models.CharField(max_length=30, choices=DocType.choices)
    file_name     = models.CharField(max_length=200)
    file_url      = models.TextField(help_text='S3 key or local path')
    uploaded_at   = models.DateTimeField(auto_now_add=True)
    uploaded_by   = models.ForeignKey(
        'users.User', null=True, on_delete=models.SET_NULL, related_name='+'
    )
    is_verified   = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.document_type} – {self.customer.company_name}"

    class Meta:
        db_table = 'customer_documents'
