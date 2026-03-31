from django.contrib import admin
from .models import Shipment, Container, ShipmentTracking

class ContainerInline(admin.TabularInline):
    model = Container
    extra = 0

class TrackingInline(admin.TabularInline):
    model = ShipmentTracking
    extra = 0
    readonly_fields = ["created_at"]

@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ["shipment_number", "customer", "mode", "origin",
                    "destination", "status", "eta", "created_at"]
    list_filter  = ["status", "mode"]
    search_fields = ["shipment_number", "mbl_number", "hbl_number", "vessel_name"]
    inlines = [ContainerInline, TrackingInline]
