"""
apps/vendors/views.py
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Vendor, VendorRate, VendorPayment
from .serializers import (
    VendorListSerializer, VendorDetailSerializer, VendorWriteSerializer,
    VendorRateSerializer, VendorPaymentSerializer,
)
from apps.users.permissions import IsAdminOrManager


class VendorViewSet(viewsets.ModelViewSet):
    queryset = Vendor.objects.prefetch_related('rates')
    permission_classes = [IsAuthenticated]
    search_fields = ['name', 'gst', 'contact_email']
    ordering_fields = ['name', 'service_type', 'created_at']
    ordering = ['name']

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return VendorWriteSerializer
        if self.action == 'retrieve':
            return VendorDetailSerializer
        return VendorListSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        vendor = self.get_object()
        vendor.status = Vendor.Status.INACTIVE
        vendor.save()
        return Response({'detail': 'Vendor deactivated.'})

    @action(detail=True, methods=['get', 'post'], url_path='rates')
    def rates(self, request, pk=None):
        vendor = self.get_object()
        if request.method == 'GET':
            return Response(VendorRateSerializer(vendor.rates.all(), many=True).data)
        serializer = VendorRateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(vendor=vendor)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class VendorPaymentViewSet(viewsets.ModelViewSet):
    queryset = VendorPayment.objects.select_related('vendor', 'shipment')
    serializer_class = VendorPaymentSerializer
    permission_classes = [IsAuthenticated, IsAdminOrManager]
    search_fields = ['payment_number', 'vendor__name']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        vp = self.get_object()
        if vp.status != VendorPayment.Status.PENDING:
            return Response({'detail': 'Only PENDING payments can be approved.'},
                            status=status.HTTP_400_BAD_REQUEST)
        vp.status = VendorPayment.Status.APPROVED
        vp.save()
        return Response({'detail': 'Vendor payment approved.'})

    @action(detail=True, methods=['post'], url_path='mark-paid')
    def mark_paid(self, request, pk=None):
        vp = self.get_object()
        vp.status = VendorPayment.Status.PAID
        vp.payment_date = request.data.get('payment_date') or vp.payment_date
        vp.reference_number = request.data.get('reference_number', vp.reference_number)
        vp.save()
        return Response({'detail': 'Vendor payment marked as paid.'})
