"""
apps/quotations/serializers.py
"""

from rest_framework import serializers
from .models import Quotation, QuotationItem, ChargeType


class ChargeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChargeType
        fields = '__all__'


class QuotationItemSerializer(serializers.ModelSerializer):
    charge_type_name = serializers.CharField(source='charge_type.name', read_only=True)

    class Meta:
        model  = QuotationItem
        fields = ['id', 'charge_type', 'charge_type_name', 'description',
                  'quantity', 'unit', 'unit_price', 'amount']
        read_only_fields = ['amount']


class QuotationListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.company_name', read_only=True)

    class Meta:
        model  = Quotation
        fields = ['id', 'quotation_number', 'customer', 'customer_name',
                  'origin', 'destination', 'mode', 'total_amount',
                  'currency', 'status', 'validity_date', 'created_at']


class QuotationDetailSerializer(serializers.ModelSerializer):
    items         = QuotationItemSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.company_name', read_only=True)

    class Meta:
        model  = Quotation
        fields = '__all__'


class QuotationWriteSerializer(serializers.ModelSerializer):
    items = QuotationItemSerializer(many=True, required=False)

    class Meta:
        model  = Quotation
        exclude = ['quotation_number', 'subtotal', 'gst_amount', 'total_amount',
                   'created_by', 'updated_by']

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        quotation  = Quotation.objects.create(**validated_data)
        for item_data in items_data:
            QuotationItem.objects.create(quotation=quotation, **item_data)
        return quotation

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                QuotationItem.objects.create(quotation=instance, **item_data)
        return instance
