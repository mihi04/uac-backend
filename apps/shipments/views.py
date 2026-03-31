"""
apps/shipments/views.py
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Shipment, Container, ShipmentTracking
from .serializers import (
    ShipmentListSerializer, ShipmentDetailSerializer, ShipmentWriteSerializer,
    ContainerSerializer, ShipmentTrackingSerializer,
)


class ShipmentViewSet(viewsets.ModelViewSet):
    queryset = Shipment.objects.select_related('customer', 'vendor').prefetch_related(
        'containers', 'tracking_events'
    )
    permission_classes = [IsAuthenticated]
    search_fields = ['shipment_number', 'customer__company_name',
                     'mbl_number', 'hbl_number', 'awb_number', 'vessel_name']
    ordering_fields = ['created_at', 'eta', 'status', 'selling_amount']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return ShipmentWriteSerializer
        if self.action == 'retrieve':
            return ShipmentDetailSerializer
        return ShipmentListSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=True, methods=['post'], url_path='update-status')
    def update_status(self, request, pk=None):
        shipment   = self.get_object()
        new_status = request.data.get('status')
        location   = request.data.get('location', '')
        description = request.data.get('description', '')
        event_date = request.data.get('event_date')

        if new_status not in dict(Shipment.Status.choices):
            return Response({'status': f"Invalid status. Choices: "
                             f"{list(dict(Shipment.Status.choices).keys())}"},
                            status=status.HTTP_400_BAD_REQUEST)

        shipment.status = new_status
        shipment.save(update_fields=['status'])

        if event_date:
            ShipmentTracking.objects.create(
                shipment=shipment,
                status=new_status,
                location=location,
                description=description,
                event_date=event_date,
                recorded_by=request.user,
            )

        return Response({'detail': 'Status updated.', 'status': new_status})

    @action(detail=True, methods=['get', 'post'], url_path='containers')
    def containers(self, request, pk=None):
        shipment = self.get_object()
        if request.method == 'GET':
            return Response(ContainerSerializer(shipment.containers.all(), many=True).data)
        serializer = ContainerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(shipment=shipment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='tracking')
    def tracking(self, request, pk=None):
        shipment = self.get_object()
        events   = shipment.tracking_events.all()
        return Response(ShipmentTrackingSerializer(events, many=True).data)

    @action(detail=True, methods=['post'], url_path='create-invoice')
    def create_invoice(self, request, pk=None):
        shipment = self.get_object()
        if hasattr(shipment, 'invoice'):
            return Response({'detail': 'Invoice already exists for this shipment.'},
                            status=status.HTTP_400_BAD_REQUEST)
        from apps.invoices.models import Invoice
        invoice = Invoice.objects.create(
            shipment=shipment,
            customer=shipment.customer,
            created_by=request.user,
            updated_by=request.user,
        )
        return Response({'detail': 'Invoice created.', 'invoice_id': invoice.id},
                        status=status.HTTP_201_CREATED)


# ── URL config ────────────────────────────────────────────────────────────────
"""apps/shipments/urls.py"""
