"""
apps/customers/views.py
"""

import os
import uuid
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated

from .models import Customer, CustomerContact, CustomerAddress, CustomerDocument
from .serializers import (
    CustomerListSerializer, CustomerDetailSerializer, CustomerWriteSerializer,
    CustomerContactSerializer, CustomerAddressSerializer, CustomerDocumentSerializer,
)


class CustomerViewSet(viewsets.ModelViewSet):
    """
    CRUD for Customers.
    GET    /customers/             list
    POST   /customers/             create
    GET    /customers/{id}/        detail
    PUT    /customers/{id}/        update
    PATCH  /customers/{id}/        partial update
    DELETE /customers/{id}/        soft-delete (status=inactive)
    """

    queryset = Customer.objects.prefetch_related(
        'contacts', 'addresses', 'documents'
    ).select_related('assigned_to')
    permission_classes = [IsAuthenticated]
    search_fields = ['company_name', 'gst', 'pan', 'iec']
    ordering_fields = ['company_name', 'created_at', 'credit_limit']
    ordering = ['company_name']

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return CustomerWriteSerializer
        if self.action == 'retrieve':
            return CustomerDetailSerializer
        return CustomerListSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        customer = self.get_object()
        customer.status = Customer.Status.INACTIVE
        customer.save()
        return Response({'detail': 'Customer deactivated.'}, status=status.HTTP_200_OK)

    # ── Sub-resources ─────────────────────────────────────────────────────────
    @action(detail=True, methods=['get', 'post'], url_path='contacts')
    def contacts(self, request, pk=None):
        customer = self.get_object()
        if request.method == 'GET':
            qs = customer.contacts.all()
            return Response(CustomerContactSerializer(qs, many=True).data)
        serializer = CustomerContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(customer=customer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'], url_path=r'contacts/(?P<contact_id>\d+)')
    def patch_contact(self, request, pk=None, contact_id=None):
        customer = self.get_object()
        contact = get_object_or_404(CustomerContact, pk=contact_id, customer=customer)
        serializer = CustomerContactSerializer(contact, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'], url_path='addresses')
    def addresses(self, request, pk=None):
        customer = self.get_object()
        if request.method == 'GET':
            return Response(CustomerAddressSerializer(customer.addresses.all(), many=True).data)
        serializer = CustomerAddressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(customer=customer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'], url_path=r'addresses/(?P<address_id>\d+)')
    def patch_address(self, request, pk=None, address_id=None):
        customer = self.get_object()
        addr = get_object_or_404(CustomerAddress, pk=address_id, customer=customer)
        serializer = CustomerAddressSerializer(addr, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'],
            url_path='documents', parser_classes=[MultiPartParser, FormParser])
    def documents(self, request, pk=None):
        customer = self.get_object()
        if request.method == 'GET':
            return Response(CustomerDocumentSerializer(customer.documents.all(), many=True).data)

        file = request.FILES.get('file')
        if not file:
            return Response({'file': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)

        # Save file locally (swap for S3 in production)
        ext = os.path.splitext(file.name)[1]
        filename = f"{uuid.uuid4().hex}{ext}"
        save_dir = os.path.join(settings.MEDIA_ROOT, 'customer_docs', str(customer.id))
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, filename)
        with open(filepath, 'wb+') as dest:
            for chunk in file.chunks():
                dest.write(chunk)

        relative_url = f"customer_docs/{customer.id}/{filename}"
        doc = CustomerDocument.objects.create(
            customer=customer,
            document_type=request.data.get('document_type', 'other'),
            file_name=file.name,
            file_url=relative_url,
            uploaded_by=request.user,
        )
        return Response(CustomerDocumentSerializer(doc).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'], url_path='documents/(?P<doc_id>[0-9]+)/verify')
    def verify_document(self, request, pk=None, doc_id=None):
        doc = CustomerDocument.objects.get(pk=doc_id, customer=self.get_object())
        doc.is_verified = True
        doc.save()
        return Response({'detail': 'Document verified.'})
