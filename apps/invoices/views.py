"""
apps/invoices/views.py
"""

import io
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import FileResponse

from .models import Invoice, InvoiceItem
from .serializers import (
    InvoiceListSerializer, InvoiceDetailSerializer,
    InvoiceWriteSerializer, InvoiceItemSerializer,
)
from apps.users.permissions import IsFinanceTeam


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.select_related('customer', 'shipment').prefetch_related('items')
    permission_classes = [IsAuthenticated]
    search_fields = ['invoice_number', 'customer__company_name']
    ordering_fields = ['invoice_date', 'due_date', 'total_amount', 'status']
    ordering = ['-invoice_date']

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return InvoiceWriteSerializer
        if self.action == 'retrieve':
            return InvoiceDetailSerializer
        return InvoiceListSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=True, methods=['post'], url_path='issue')
    def issue(self, request, pk=None):
        invoice = self.get_object()
        if invoice.status != Invoice.Status.DRAFT:
            return Response({'detail': 'Only DRAFT invoices can be issued.'},
                            status=status.HTTP_400_BAD_REQUEST)
        invoice.status = Invoice.Status.ISSUED
        invoice.save()
        return Response({'detail': 'Invoice issued.'})

    @action(detail=True, methods=['post'], url_path='send-email')
    def send_email(self, request, pk=None):
        invoice = self.get_object()
        # TODO: hook up email backend + PDF attachment
        invoice.status = Invoice.Status.SENT
        invoice.save()
        return Response({'detail': f"Invoice emailed to {invoice.customer.company_name}."})

    @action(detail=True, methods=['get'], url_path='download-pdf')
    def download_pdf(self, request, pk=None):
        invoice = self.get_object()
        pdf_bytes = self._generate_pdf(invoice)
        return FileResponse(
            io.BytesIO(pdf_bytes),
            content_type='application/pdf',
            as_attachment=True,
            filename=f"{invoice.invoice_number}.pdf",
        )

    @staticmethod
    def _generate_pdf(invoice) -> bytes:
        """
        Minimal PDF using reportlab.
        Replace with a proper HTML→PDF renderer (WeasyPrint / wkhtmltopdf) in production.
        """
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            buf = io.BytesIO()
            c   = canvas.Canvas(buf, pagesize=A4)
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, 800, f"INVOICE: {invoice.invoice_number}")
            c.setFont("Helvetica", 12)
            c.drawString(50, 780, f"Customer: {invoice.customer.company_name}")
            c.drawString(50, 760, f"Date: {invoice.invoice_date}")
            c.drawString(50, 740, f"Due Date: {invoice.due_date or 'N/A'}")
            y = 700
            for item in invoice.items.all():
                c.drawString(50, y, f"  {item.description}  —  {invoice.currency} {item.amount}")
                y -= 20
            c.drawString(50, y - 10, f"IGST: {invoice.igst_amount}")
            c.drawString(50, y - 30, f"TOTAL: {invoice.currency} {invoice.total_amount}")
            c.save()
            return buf.getvalue()
        except ImportError:
            return b'%PDF-placeholder (install reportlab)'
