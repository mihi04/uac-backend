from django.contrib import admin
from .models import Invoice, InvoiceItem

class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display  = ["invoice_number", "customer", "invoice_date", "due_date",
                     "total_amount", "amount_paid", "balance_due", "status"]
    list_filter   = ["status", "invoice_type", "is_interstate"]
    search_fields = ["invoice_number", "customer__company_name"]
    inlines       = [InvoiceItemInline]
    readonly_fields = ["subtotal", "total_gst", "total_amount",
                       "igst_amount", "cgst_amount", "sgst_amount", "balance_due"]
