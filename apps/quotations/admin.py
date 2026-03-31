from django.contrib import admin
from .models import Quotation, QuotationItem, ChargeType

class QuotationItemInline(admin.TabularInline):
    model = QuotationItem
    extra = 0

@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ["quotation_number", "customer", "mode", "total_amount",
                    "currency", "status", "created_at"]
    list_filter  = ["status", "mode"]
    search_fields = ["quotation_number", "customer__company_name"]
    inlines = [QuotationItemInline]

@admin.register(ChargeType)
class ChargeTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "is_taxable"]
