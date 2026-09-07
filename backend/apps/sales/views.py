"""Sale views."""

import logging
from decimal import Decimal

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from apps.accounts.permissions import HasModulePermission
from apps.customers.models import Customer

from .finance import aggregate_sales
from .models import Payment, Sale, SaleItem
from .serializers import (
    PaymentSerializer,
    SaleCreateSerializer,
    SaleDetailSerializer,
    SaleListSerializer,
    SaleReturnSerializer,
)
from .services import SaleService

logger = logging.getLogger(__name__)


class SaleViewSet(viewsets.ModelViewSet):
    required_module = "pos"
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["payment_method", "status", "cashier"]
    search_fields = ["sale_number", "customer__full_name"]
    ordering_fields = ["created_at", "total"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Sale.objects.select_related("cashier", "customer").prefetch_related("items", "payments").all()

    def get_serializer_class(self):
        if self.action == "list":
            return SaleListSerializer
        if self.action == "create":
            return SaleCreateSerializer
        return SaleDetailSerializer

    def get_permissions(self):
        # HasModulePermission required_module='pos' allaqachon foydalanuvchining
        # POS bo'limiga ruxsati borligini tekshiradi. Qo'shimcha rol tekshiruvi
        # (IsCashierOrAdmin) ombor mudiri kabi ruxsat berilgan rollarga to'siq
        # bo'lardi.
        if self.action in ("list", "retrieve", "metadata"):
            return [HasModulePermission()]
        return [HasModulePermission()]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # Summary FILTRLANGAN queryset ustidan, lekin:
        #  - bekor qilingan savdolar hisobga kirmaydi,
        #  - qaytarilgan qism ayiriladi (sof tushum).
        # Ilgari ikkalasi ham to'liq summasi bilan qo'shilardi.
        summary = aggregate_sales(queryset)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data["summary"] = summary
            return response

        serializer = self.get_serializer(queryset, many=True)
        return Response({"results": serializer.data, "summary": summary})

    def create(self, request, *args, **kwargs):
        serializer = SaleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        customer = None
        if data.get("customer_id"):
            try:
                customer = Customer.objects.get(pk=data["customer_id"])
            except Customer.DoesNotExist:
                return Response(
                    {"success": False, "message": "Mijoz topilmadi.", "errors": {}}, status=status.HTTP_404_NOT_FOUND
                )
        elif data.get("customer_name"):
            customer_name = data["customer_name"].strip()
            customer_phone = data.get("customer_phone", "").strip()
            customer, created = Customer.objects.get_or_create(
                full_name=customer_name, defaults={"phone": customer_phone}
            )
            if not created and customer_phone and customer.phone != customer_phone:
                customer.phone = customer_phone
                customer.save(update_fields=["phone", "updated_at"])

        try:
            sale, change_amount = SaleService.create_sale(
                items_data=data["items"],
                payment_method=data["payment_method"],
                cashier=request.user,
                customer=customer,
                discount=Decimal(str(data.get("discount", 0))),
                paid_amount=data.get("paid_amount"),
                due_date=data.get("due_date"),
            )
        except ValueError as e:
            return Response({"success": False, "message": str(e), "errors": {}}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            # Foydalanuvchiga ichki tafsilotni ko'rsatmaymiz, lekin log'siz
            # 500 xatoni keyin umuman tekshirib bo'lmaydi.
            logger.exception("Savdo yaratishda kutilmagan xatolik")
            return Response(
                {"success": False, "message": "Savdo yaratishda xatolik yuz berdi.", "errors": {}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "success": True,
                "message": "Savdo muvaffaqiyatli yakunlandi.",
                "data": SaleDetailSerializer(sale).data,
                "change_amount": str(change_amount),
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="return")
    def return_item(self, request, pk=None):
        """Process a sale return."""
        serializer = SaleReturnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            sale_item = SaleItem.objects.select_related("sale", "product").get(
                pk=serializer.validated_data["sale_item_id"],
                sale_id=pk,
            )
        except SaleItem.DoesNotExist:
            return Response(
                {"success": False, "message": "Savdo elementi topilmadi.", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            SaleService.return_sale_item(
                sale_item=sale_item,
                return_quantity=serializer.validated_data["return_quantity"],
                user=request.user,
            )
        except ValueError as e:
            return Response({"success": False, "message": str(e), "errors": {}}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "success": True,
                "message": "Mahsulot muvaffaqiyatli qaytarildi.",
            }
        )

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel_sale(self, request, pk=None):
        """Cancel an entire sale.

        Butun amal servisda, bitta tranzaksiyada bajariladi: tovar omborga
        qaytadi, pul qaytarimi yoziladi va nasiya savdo bo'lsa qarz yopiladi.
        """
        sale = self.get_object()

        try:
            SaleService.cancel_sale(sale=sale, user=request.user)
        except ValueError as e:
            return Response({"success": False, "message": str(e), "errors": {}}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Savdoni bekor qilishda kutilmagan xatolik")
            return Response(
                {"success": False, "message": "Savdoni bekor qilishda xatolik yuz berdi.", "errors": {}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "success": True,
                "message": "Savdo bekor qilindi.",
            }
        )


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentSerializer
    required_module = "pos"
    permission_classes = [HasModulePermission]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["sale", "payment_method"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Payment.objects.select_related("sale", "created_by").all()
