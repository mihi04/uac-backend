"""apps/quotations/urls.py"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import QuotationViewSet, ChargeTypeViewSet

router = DefaultRouter()
router.register('charge-types', ChargeTypeViewSet, basename='charge-types')
router.register('', QuotationViewSet, basename='quotations')

urlpatterns = [path('', include(router.urls))]
