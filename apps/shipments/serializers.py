"""
apps/shipments/serializers.py
"""

from rest_framework import serializers
from .models import Shipment, Container, ShipmentTracking


class ContainerSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Container
        fields = ['id', 'container_number', 'container_type', 'seal_number',
                  'gross_weight', 'cbm', 'packages', 'description']


class ShipmentTrackingSerializer(serializers.ModelSerializer):
    recorded_by_name = serializers.CharField(source='recorded_by.name', read_only=True)

    class Meta:
        model  = ShipmentTracking
        fields = ['id', 'status', 'location', 'description', 'event_date',
                  'recorded_by_name', 'created_at']


class ShipmentListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.company_name', read_only=True)
    profit        = serializers.ReadOnlyField()
    profit_margin = serializers.ReadOnlyField()

    class Meta:
        model  = Shipment
        fields = ['id', 'shipment_number', 'customer', 'customer_name',
                  'mode', 'origin', 'destination', 'status', 'eta',
                  'selling_amount', 'buying_amount', 'profit', 'profit_margin',
                  'created_at']


class ShipmentDetailSerializer(serializers.ModelSerializer):
    containers      = ContainerSerializer(many=True, read_only=True)
    tracking_events = ShipmentTrackingSerializer(many=True, read_only=True)
    customer_name   = serializers.CharField(source='customer.company_name', read_only=True)
    profit          = serializers.ReadOnlyField()
    profit_margin   = serializers.ReadOnlyField()

    class Meta:
        model  = Shipment
        fields = '__all__'


class ShipmentWriteSerializer(serializers.ModelSerializer):
    containers = ContainerSerializer(many=True, required=False)

    class Meta:
        model   = Shipment
        exclude = ['shipment_number', 'created_by', 'updated_by']

    def create(self, validated_data):
        containers_data = validated_data.pop('containers', [])
        shipment = Shipment.objects.create(**validated_data)
        for c in containers_data:
            Container.objects.create(shipment=shipment, **c)
        return shipment

    def update(self, instance, validated_data):
        validated_data.pop('containers', None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        return instance
