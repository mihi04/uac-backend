"""apps/invoices/urls.py"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InvoiceViewSet

router = DefaultRouter()
router.register('', InvoiceViewSet, basename='invoices')
urlpatterns = [path('', include(router.urls))]
