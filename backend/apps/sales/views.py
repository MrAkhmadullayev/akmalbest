"""Sale views."""
from decimal import Decimal
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Sale, SaleItem, Payment
from .serializers import (
    SaleListSerializer, SaleDetailSerializer,
    SaleCreateSerializer, SaleReturnSerializer, PaymentSerializer,
)
from .services import SaleService
from apps.accounts.permissions import IsCashierOrAdmin, IsAdmin
from apps.customers.models import Customer


class SaleViewSet(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['payment_method', 'status', 'cashier']
    search_fields = ['sale_number', 'customer__full_name']
    ordering_fields = ['created_at', 'total']
    ordering = ['-created_at']

    def get_queryset(self):
        return Sale.objects.select_related(
            'cashier', 'customer'
        ).prefetch_related('items', 'payments').all()

    def get_serializer_class(self):
        if self.action == 'list':
            return SaleListSerializer
        if self.action == 'create':
            return SaleCreateSerializer
        return SaleDetailSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        return [IsCashierOrAdmin()]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # We calculate summary on the *filtered* queryset
        from django.db.models import Sum
        from decimal import Decimal
        
        summary = {
            'total_sales': queryset.aggregate(t=Sum('total'))['t'] or Decimal('0'),
            'cash_sales': queryset.filter(payment_method='CASH').aggregate(t=Sum('total'))['t'] or Decimal('0'),
            'card_sales': queryset.filter(payment_method='CARD').aggregate(t=Sum('total'))['t'] or Decimal('0'),
            'debt_sales': queryset.filter(payment_method='DEBT').aggregate(t=Sum('total'))['t'] or Decimal('0'),
        }

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data['summary'] = summary
            return response

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'results': serializer.data,
            'summary': summary
        })

    def create(self, request, *args, **kwargs):
        serializer = SaleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        customer = None
        if data.get('customer_id'):
            try:
                customer = Customer.objects.get(pk=data['customer_id'])
            except Customer.DoesNotExist:
                return Response(
                    {"success": False, "message": "Mijoz topilmadi.", "errors": {}},
                    status=status.HTTP_404_NOT_FOUND
                )
        elif data.get('customer_name'):
            customer_name = data['customer_name'].strip()
            customer_phone = data.get('customer_phone', '').strip()
            customer, created = Customer.objects.get_or_create(
                full_name=customer_name,
                defaults={'phone': customer_phone}
            )
            if not created and customer_phone and customer.phone != customer_phone:
                customer.phone = customer_phone
                customer.save(update_fields=['phone', 'updated_at'])

        try:
            sale, change_amount = SaleService.create_sale(
                items_data=data['items'],
                payment_method=data['payment_method'],
                cashier=request.user,
                customer=customer,
                discount=Decimal(str(data.get('discount', 0))),
                paid_amount=data.get('paid_amount'),
                due_date=data.get('due_date'),
            )
        except ValueError as e:
            return Response(
                {"success": False, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"success": False, "message": "Savdo yaratishda xatolik yuz berdi.", "errors": {}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            "success": True,
            "message": "Savdo muvaffaqiyatli yakunlandi.",
            "data": SaleDetailSerializer(sale).data,
            "change_amount": str(change_amount),
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='return')
    def return_item(self, request, pk=None):
        """Process a sale return."""
        serializer = SaleReturnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            sale_item = SaleItem.objects.select_related('sale', 'product').get(
                pk=serializer.validated_data['sale_item_id'],
                sale_id=pk,
            )
        except SaleItem.DoesNotExist:
            return Response(
                {"success": False, "message": "Savdo elementi topilmadi.", "errors": {}},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            SaleService.return_sale_item(
                sale_item=sale_item,
                return_quantity=serializer.validated_data['return_quantity'],
                user=request.user,
            )
        except ValueError as e:
            return Response(
                {"success": False, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            "success": True,
            "message": "Mahsulot muvaffaqiyatli qaytarildi.",
        })

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel_sale(self, request, pk=None):
        """Cancel an entire sale."""
        sale = self.get_object()
        if sale.status != 'COMPLETED':
            return Response(
                {"success": False, "message": "Faqat bajarilgan savdolarni bekor qilish mumkin.", "errors": {}},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Return all items to inventory
        for item in sale.items.all():
            remaining = item.quantity - item.returned_quantity
            if remaining > 0:
                SaleService.return_sale_item(item, remaining, request.user)

        sale.status = 'CANCELLED'
        sale.save(update_fields=['status', 'updated_at'])

        return Response({
            "success": True,
            "message": "Savdo bekor qilindi.",
        })


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['sale', 'payment_method']
    ordering = ['-created_at']

    def get_queryset(self):
        return Payment.objects.select_related('sale', 'created_by').all()
