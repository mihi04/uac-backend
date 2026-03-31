"""apps/vendors/urls.py"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import VendorViewSet, VendorPaymentViewSet

router = DefaultRouter()
router.register('payments', VendorPaymentViewSet, basename='vendor-payments')
router.register('', VendorViewSet, basename='vendors')
urlpatterns = [path('', include(router.urls))]
