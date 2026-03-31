"""
apps/quotations/views.py
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Quotation, QuotationItem, ChargeType
from .serializers import (
    QuotationListSerializer, QuotationDetailSerializer,
    QuotationWriteSerializer, QuotationItemSerializer, ChargeTypeSerializer,
)


class QuotationViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for Quotations.
    Extra actions:
      POST /{id}/convert-to-shipment/  — convert approved quotation to shipment
      POST /{id}/send/                 — mark as sent to customer
    """

    queryset = Quotation.objects.select_related('customer').prefetch_related('items')
    permission_classes = [IsAuthenticated]
    search_fields = ['quotation_number', 'customer__company_name', 'origin', 'destination']
    ordering_fields = ['created_at', 'total_amount', 'status']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return QuotationWriteSerializer
        if self.action == 'retrieve':
            return QuotationDetailSerializer
        return QuotationListSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=True, methods=['post'], url_path='send')
    def send(self, request, pk=None):
        quot = self.get_object()
        if quot.status != Quotation.Status.DRAFT:
            return Response({'detail': 'Only DRAFT quotations can be sent.'},
                            status=status.HTTP_400_BAD_REQUEST)
        quot.status = Quotation.Status.SENT
        quot.save()
        # TODO: trigger email notification here
        return Response({'detail': 'Quotation marked as sent.'})

    @action(detail=True, methods=['post'], url_path='convert-to-shipment')
    def convert_to_shipment(self, request, pk=None):
        quot = self.get_object()
        if quot.status != Quotation.Status.APPROVED:
            return Response({'detail': 'Only APPROVED quotations can be converted.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if hasattr(quot, 'shipment'):
            return Response({'detail': 'Already converted.'}, status=status.HTTP_400_BAD_REQUEST)

        from apps.shipments.models import Shipment
        shipment = Shipment.objects.create(
            quotation=quot,
            customer=quot.customer,
            origin=quot.origin,
            destination=quot.destination,
            mode=quot.mode,
            currency=quot.currency,
            created_by=request.user,
            updated_by=request.user,
        )
        quot.status = Quotation.Status.CONVERTED
        quot.save()

        return Response({'detail': 'Shipment created.', 'shipment_id': shipment.id},
                        status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post', 'delete'],
            url_path='items/(?P<item_id>[0-9]+)?')
    def manage_items(self, request, pk=None, item_id=None):
        quot = self.get_object()
        if request.method == 'POST':
            serializer = QuotationItemSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(quotation=quot)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        if item_id:
            item = QuotationItem.objects.get(pk=item_id, quotation=quot)
            item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


class ChargeTypeViewSet(viewsets.ModelViewSet):
    queryset = ChargeType.objects.all()
    serializer_class = ChargeTypeSerializer
    permission_classes = [IsAuthenticated]
