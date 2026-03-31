"""
apps/invoices/serializers.py
"""

from rest_framework import serializers
from .models import Invoice, InvoiceItem


class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model  = InvoiceItem
        fields = ['id', 'description', 'hsn_sac', 'quantity', 'unit',
                  'unit_price', 'amount']
        read_only_fields = ['amount']


class InvoiceListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.company_name', read_only=True)

    class Meta:
        model  = Invoice
        fields = ['id', 'invoice_number', 'invoice_type', 'customer', 'customer_name',
                  'invoice_date', 'due_date', 'total_amount', 'amount_paid',
                  'balance_due', 'currency', 'status']


class InvoiceDetailSerializer(serializers.ModelSerializer):
    items         = InvoiceItemSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.company_name', read_only=True)

    class Meta:
        model  = Invoice
        fields = '__all__'


class InvoiceWriteSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, required=False)

    class Meta:
        model   = Invoice
        exclude = ['invoice_number', 'subtotal', 'igst_amount', 'cgst_amount',
                   'sgst_amount', 'total_gst', 'total_amount', 'amount_paid',
                   'balance_due', 'created_by', 'updated_by', 'pdf_url']

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        invoice    = Invoice.objects.create(**validated_data)
        for item_data in items_data:
            InvoiceItem.objects.create(invoice=invoice, **item_data)
        return invoice

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                InvoiceItem.objects.create(invoice=instance, **item_data)
        return instance
