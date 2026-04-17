"""
apps/customers/serializers.py
"""

from rest_framework import serializers
from .models import Customer, CustomerContact, CustomerAddress, CustomerDocument
import re


# ── Validators ────────────────────────────────────────────────────────────────
def validate_gst(value):
    pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
    if value and not re.match(pattern, value.upper()):
        raise serializers.ValidationError('Invalid GST number format.')
    return value.upper() if value else value


def validate_pan(value):
    pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
    if value and not re.match(pattern, value.upper()):
        raise serializers.ValidationError('Invalid PAN format.')
    return value.upper() if value else value


def validate_iec(value):
    if value and len(value) != 10:
        raise serializers.ValidationError('IEC must be exactly 10 characters.')
    return value.upper() if value else value


def validate_ifsc(value):
    if not value:
        return value
    v = value.strip().upper()
    if len(v) != 11 or not re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', v):
        raise serializers.ValidationError('Invalid IFSC format (11 characters, e.g. HDFC0001234).')
    return v


# ── Contact ───────────────────────────────────────────────────────────────────
class CustomerContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerContact
        fields = ['id', 'name', 'designation', 'phone', 'email', 'is_primary']


# ── Address ───────────────────────────────────────────────────────────────────
class CustomerAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerAddress
        fields = ['id', 'address_type', 'address_line', 'city', 'state',
                  'country', 'pin_code', 'is_default']


# ── Document ──────────────────────────────────────────────────────────────────
class CustomerDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerDocument
        fields = ['id', 'document_type', 'file_name', 'file_url',
                  'uploaded_at', 'is_verified']
        read_only_fields = ['uploaded_at']


# ── Customer List ─────────────────────────────────────────────────────────────
class CustomerListSerializer(serializers.ModelSerializer):
    primary_contact_name = serializers.SerializerMethodField()
    primary_contact_email = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = ['id', 'company_name', 'business_type', 'legal_structure', 'gst', 'status',
                  'credit_limit', 'outstanding_balance', 'created_at',
                  'primary_contact_name', 'primary_contact_email']

    def _primary_contact(self, obj):
        contacts = list(obj.contacts.all())
        if not contacts:
            return None
        return next((c for c in contacts if c.is_primary), contacts[0])

    def get_primary_contact_name(self, obj):
        c = self._primary_contact(obj)
        return c.name if c else ''

    def get_primary_contact_email(self, obj):
        c = self._primary_contact(obj)
        return c.email if c else ''


# ── Customer Detail ───────────────────────────────────────────────────────────
class CustomerDetailSerializer(serializers.ModelSerializer):
    contacts  = CustomerContactSerializer(many=True, read_only=True)
    addresses = CustomerAddressSerializer(many=True, read_only=True)
    documents = CustomerDocumentSerializer(many=True, read_only=True)
    available_credit = serializers.ReadOnlyField()
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = '__all__'

    def get_assigned_to_name(self, obj):
        return obj.assigned_to.name if obj.assigned_to else None


# ── Customer Create / Update ──────────────────────────────────────────────────
class CustomerWriteSerializer(serializers.ModelSerializer):
    gst = serializers.CharField(required=False, allow_blank=True, allow_null=True, validators=[validate_gst])
    pan = serializers.CharField(required=False, allow_blank=True, validators=[validate_pan])
    iec = serializers.CharField(required=False, allow_blank=True, validators=[validate_iec])
    bank_ifsc = serializers.CharField(required=False, allow_blank=True, validators=[validate_ifsc])

    class Meta:
        model = Customer
        exclude = ['created_by', 'updated_by', 'outstanding_balance']

    def validate_credit_limit(self, value):
        if value < 0:
            raise serializers.ValidationError('Credit limit cannot be negative.')
        return value
