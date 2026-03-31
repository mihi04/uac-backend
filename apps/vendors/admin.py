from django.contrib import admin
from .models import Vendor, VendorRate, VendorPayment

class VendorRateInline(admin.TabularInline):
    model = VendorRate
    extra = 0

@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display  = ["name", "service_type", "contact_email", "status", "credit_limit"]
    list_filter   = ["status", "service_type"]
    search_fields = ["name", "gst"]
    inlines       = [VendorRateInline]

@admin.register(VendorPayment)
class VendorPaymentAdmin(admin.ModelAdmin):
    list_display = ["payment_number", "vendor", "amount", "due_date",
                    "payment_date", "status"]
    list_filter  = ["status"]
    search_fields = ["payment_number", "vendor__name"]
