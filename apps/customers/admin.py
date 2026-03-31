from django.contrib import admin
from .models import Customer, CustomerContact, CustomerAddress, CustomerDocument

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display  = ["company_name", "business_type", "gst", "status",
                     "credit_limit", "outstanding_balance", "created_at"]
    list_filter   = ["status", "business_type"]
    search_fields = ["company_name", "gst", "pan", "iec"]

@admin.register(CustomerContact)
class CustomerContactAdmin(admin.ModelAdmin):
    list_display = ["name", "customer", "designation", "phone", "email", "is_primary"]
    search_fields = ["name", "customer__company_name"]

@admin.register(CustomerDocument)
class CustomerDocumentAdmin(admin.ModelAdmin):
    list_display = ["customer", "document_type", "is_verified", "uploaded_at"]
    list_filter  = ["document_type", "is_verified"]
