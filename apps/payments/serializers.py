"""
apps/payments/serializers.py
"""

from rest_framework import serializers
from .models import Payment, Transaction


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Transaction
        fields = ['id', 'tx_type', 'account', 'amount', 'narration', 'created_at']


class PaymentListSerializer(serializers.ModelSerializer):
    customer_name  = serializers.CharField(source='customer.company_name', read_only=True)
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)

    class Meta:
        model  = Payment
        fields = ['id', 'payment_number', 'customer', 'customer_name',
                  'invoice', 'invoice_number', 'amount', 'currency',
                  'payment_method', 'payment_date', 'status', 'reconciled']


class PaymentDetailSerializer(serializers.ModelSerializer):
    transactions   = TransactionSerializer(many=True, read_only=True)
    customer_name  = serializers.CharField(source='customer.company_name', read_only=True)
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)

    class Meta:
        model  = Payment
        fields = '__all__'


class PaymentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model   = Payment
        exclude = ['payment_number', 'reconciled', 'reconciled_by',
                   'reconciled_at', 'created_by', 'updated_by']

    def validate(self, data):
        invoice = data.get('invoice')
        amount  = data.get('amount', 0)
        if invoice and amount > invoice.balance_due:
            raise serializers.ValidationError(
                f"Payment amount ({amount}) exceeds invoice balance due "
                f"({invoice.balance_due})."
            )
        return data
