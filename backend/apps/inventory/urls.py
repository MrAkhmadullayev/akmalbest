"""Inventory URL configuration."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InventoryViewSet, InventoryAdjustView, InventoryTransactionViewSet

router = DefaultRouter()
router.register(r'inventory', InventoryViewSet, basename='inventory')
router.register(r'inventory/transactions', InventoryTransactionViewSet, basename='inventory-transactions')

urlpatterns = [
    path('inventory/adjust/', InventoryAdjustView.as_view(), name='inventory-adjust'),
    path('', include(router.urls)),
]
