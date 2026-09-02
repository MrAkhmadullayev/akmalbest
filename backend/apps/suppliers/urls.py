"""Supplier URL configuration."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PurchaseViewSet, SupplierViewSet

router = DefaultRouter()
router.register(r'suppliers', SupplierViewSet, basename='suppliers')
router.register(r'purchases', PurchaseViewSet, basename='purchases')

urlpatterns = [path('', include(router.urls))]
