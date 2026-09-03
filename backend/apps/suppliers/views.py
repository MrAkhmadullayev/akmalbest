"""Supplier views."""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from apps.accounts.permissions import HasModulePermission, IsAdminOrWarehouseManager

from .models import Purchase, Supplier
from .serializers import PurchaseCreateSerializer, PurchaseSerializer, SupplierSerializer
from .services import PurchaseService


class SupplierViewSet(viewsets.ModelViewSet):
    required_module = 'suppliers'
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'contact_person', 'phone']
    ordering_fields = ['name', 'created_at']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [HasModulePermission()]
        return [HasModulePermission(), IsAdminOrWarehouseManager()]


class PurchaseViewSet(viewsets.ModelViewSet):
    serializer_class = PurchaseSerializer
    required_module = 'suppliers'
    permission_classes = [HasModulePermission, IsAdminOrWarehouseManager]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['supplier', 'status']
    search_fields = ['invoice_number', 'supplier__name']
    ordering_fields = ['purchase_date', 'total', 'created_at']
    ordering = ['-purchase_date']

    def get_queryset(self):
        return Purchase.objects.select_related('supplier', 'created_by').prefetch_related('items__product').all()

    def get_serializer_class(self):
        if self.action == 'create':
            return PurchaseCreateSerializer
        return PurchaseSerializer

    def create(self, request, *args, **kwargs):
        serializer = PurchaseCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            supplier = Supplier.objects.get(pk=data['supplier'])
        except Supplier.DoesNotExist:
            return Response(
                {"success": False, "message": "Yetkazib beruvchi topilmadi.", "errors": {}},
                status=status.HTTP_404_NOT_FOUND
            )

        purchase = PurchaseService.create_purchase(
            supplier=supplier,
            items_data=data['items'],
            user=request.user,
            invoice_number=data.get('invoice_number', ''),
            purchase_date=data.get('purchase_date'),
            notes=data.get('notes', ''),
        )

        return Response({
            "success": True,
            "message": "Xarid muvaffaqiyatli yaratildi.",
            "data": PurchaseSerializer(purchase).data,
        }, status=status.HTTP_201_CREATED)
