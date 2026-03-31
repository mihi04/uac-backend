"""
apps/vendors/serializers.py
"""

from rest_framework import serializers
from .models import Vendor, VendorRate, VendorPayment


class VendorRateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = VendorRate
        fields = '__all__'
        read_only_fields = ['created_at']


class VendorListSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Vendor
        fields = ['id', 'name', 'service_type', 'contact_email',
                  'contact_phone', 'status', 'credit_limit']


class VendorDetailSerializer(serializers.ModelSerializer):
    rates = VendorRateSerializer(many=True, read_only=True)

    class Meta:
        model  = Vendor
        fields = '__all__'


class VendorWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model   = Vendor
        exclude = ['created_by', 'updated_by']


class VendorPaymentSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)

    class Meta:
        model  = VendorPayment
        fields = '__all__'
        read_only_fields = ['payment_number', 'created_by', 'updated_by']
