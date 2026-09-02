"""
Product views and viewsets.
"""
from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Category, Brand, Product
from .serializers import (
    CategorySerializer, BrandSerializer,
    ProductListSerializer, ProductDetailSerializer,
    ProductCreateUpdateSerializer, ProductBarcodeLookupSerializer,
)
from apps.accounts.permissions import IsAdmin, IsAdminOrWarehouseManager
from apps.audit.services import AuditService


class CategoryViewSet(viewsets.ModelViewSet):
    """Category CRUD."""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        return [IsAdminOrWarehouseManager()]


class BrandViewSet(viewsets.ModelViewSet):
    """Brand CRUD."""
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        return [IsAdminOrWarehouseManager()]


class ProductViewSet(viewsets.ModelViewSet):
    """Product CRUD with filtering and search."""
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'brand', 'is_active', 'unit']
    search_fields = ['name', 'barcode', 'description']
    ordering_fields = ['name', 'selling_price', 'current_stock', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        return Product.objects.select_related('category', 'brand', 'supplier').all()

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductListSerializer
        elif self.action in ('create', 'update', 'partial_update'):
            return ProductCreateUpdateSerializer
        return ProductDetailSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        return [IsAdminOrWarehouseManager()]

    def perform_create(self, serializer):
        initial_stock = serializer.validated_data.pop('initial_stock', 0)
        payment_method = serializer.validated_data.pop('payment_method', 'CASH')
        product = serializer.save()
        
        # Create inventory record for new product
        from apps.inventory.models import Inventory
        Inventory.objects.get_or_create(product=product, defaults={'quantity': 0})
        
        # Add initial stock as a batch
        if initial_stock > 0:
            from apps.inventory.services import InventoryService
            from apps.inventory.models import TransactionType
            InventoryService.increase_stock(
                product=product,
                quantity=initial_stock,
                transaction_type=TransactionType.PURCHASE,
                reference_id=str(product.id),
                reference_type='INITIAL_STOCK',
                user=self.request.user,
                notes="Boshlang'ich qoldiq",
                purchase_price=product.purchase_price,
                payment_method=payment_method
            )
            
        # Audit log
        AuditService.log(
            user=self.request.user,
            action='CREATE',
            model_name='Product',
            object_id=str(product.id),
            new_data=ProductDetailSerializer(product).data,
        )

    def perform_update(self, serializer):
        old_data = ProductDetailSerializer(self.get_object()).data
        product = serializer.save()
        AuditService.log(
            user=self.request.user,
            action='UPDATE',
            model_name='Product',
            object_id=str(product.id),
            old_data=old_data,
            new_data=ProductDetailSerializer(product).data,
        )

    def destroy(self, request, *args, **kwargs):
        from django.db.models import ProtectedError
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": "Bu mahsulot bilan bog'liq savdo hujjatlari mavjud bo'lganligi sababli uni o'chirib bo'lmaydi."},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrWarehouseManager])
    def add_stock(self, request, pk=None):
        product = self.get_object()
        quantity = request.data.get('quantity', 0)
        purchase_price = request.data.get('purchase_price')
        payment_method = request.data.get('payment_method', 'CASH')
        notes = request.data.get('notes', "Qo'shimcha kirim")
        
        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError
        except ValueError:
            return Response({'success': False, 'message': "Noto'g'ri miqdor."}, status=status.HTTP_400_BAD_REQUEST)
            
        if purchase_price is None:
            purchase_price = product.purchase_price
        else:
            try:
                from decimal import Decimal
                purchase_price = Decimal(str(purchase_price))
            except Exception:
                return Response({'success': False, 'message': "Noto'g'ri narx."}, status=status.HTTP_400_BAD_REQUEST)
                
        from apps.inventory.services import InventoryService
        from apps.inventory.models import TransactionType
        
        try:
            InventoryService.increase_stock(
                product=product,
                quantity=quantity,
                transaction_type=TransactionType.PURCHASE,
                reference_id=str(product.id),
                reference_type='ADD_STOCK',
                user=request.user,
                notes=notes,
                purchase_price=purchase_price,
                payment_method=payment_method
            )
            
            # Update product purchase price if it changed
            if product.purchase_price != purchase_price:
                product.purchase_price = purchase_price
                product.save(update_fields=['purchase_price', 'updated_at'])
                
        except Exception as e:
            return Response({'success': False, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
        return Response({'success': True, 'message': "Kirim muvaffaqiyatli qo'shildi."})


class ProductBarcodeLookupView(generics.RetrieveAPIView):
    """
    Ultra-fast barcode lookup for POS.
    GET /api/products/barcode/{barcode}/
    """
    serializer_class = ProductBarcodeLookupSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'barcode'

    def get_queryset(self):
        return Product.objects.select_related('category', 'brand').filter(is_active=True)

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response({
                'success': True,
                'data': serializer.data,
            })
        except Exception:
            return Response({
                'success': False,
                'message': 'Mahsulot topilmadi.',
                'errors': {},
            }, status=status.HTTP_404_NOT_FOUND)
