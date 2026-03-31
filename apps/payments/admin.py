from django.contrib import admin
from .models import Payment, Transaction

class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 0
    readonly_fields = ["created_at"]

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display  = ["payment_number", "customer", "invoice", "amount",
                     "payment_method", "payment_date", "status", "reconciled"]
    list_filter   = ["status", "payment_method", "reconciled"]
    search_fields = ["payment_number", "customer__company_name", "reference_number"]
    inlines       = [TransactionInline]
