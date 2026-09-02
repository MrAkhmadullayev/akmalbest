"""
Inventory views.
"""
from django.db import models
from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Inventory, InventoryTransaction
from .serializers import InventorySerializer, InventoryAdjustSerializer, InventoryTransactionSerializer
from .services import InventoryService
from apps.accounts.permissions import IsAdminOrWarehouseManager
from apps.products.models import Product


class InventoryViewSet(viewsets.ReadOnlyModelViewSet):
    """List inventory with stock status."""
    serializer_class = InventorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['product__name', 'product__barcode']
    ordering_fields = ['quantity', 'updated_at', 'product__name']
    ordering = ['product__name']

    def get_queryset(self):
        qs = Inventory.objects.select_related('product').all()
        stock_status = self.request.query_params.get('stock_status')
        if stock_status == 'LOW':
            qs = qs.filter(product__current_stock__lte=models.F('product__min_stock'), product__current_stock__gt=0)
        elif stock_status == 'WARNING':
            qs = qs.filter(product__current_stock__lte=models.F('product__warning_stock'), product__current_stock__gt=models.F('product__min_stock'))
        elif stock_status == 'OUT_OF_STOCK':
            qs = qs.filter(product__current_stock__lte=0)
        return qs


class InventoryAdjustView(generics.CreateAPIView):
    """Manual stock adjustment endpoint."""
    serializer_class = InventoryAdjustSerializer
    permission_classes = [IsAdminOrWarehouseManager]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            product = Product.objects.get(pk=serializer.validated_data['product_id'])
        except Product.DoesNotExist:
            return Response(
                {"success": False, "message": "Mahsulot topilmadi.", "errors": {}},
                status=status.HTTP_404_NOT_FOUND
            )

        new_qty = InventoryService.adjust_stock(
            product=product,
            new_quantity=serializer.validated_data['new_quantity'],
            user=request.user,
            notes=serializer.validated_data.get('notes', ''),
        )

        return Response({
            "success": True,
            "message": f"Ombor yangilandi. Yangi miqdor: {new_qty}",
            "data": {"new_quantity": new_qty},
        }, status=status.HTTP_200_OK)


class InventoryTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """View inventory transaction history."""
    serializer_class = InventoryTransactionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['product', 'transaction_type']
    search_fields = ['product__name', 'product__barcode', 'notes']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        return InventoryTransaction.objects.select_related('product', 'created_by').all()
