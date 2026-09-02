"""Debt views."""
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone
from rest_framework.decorators import action

from .models import Debt, DebtPayment
from .serializers import (
    DebtListSerializer, DebtDetailSerializer,
    DebtPaymentSerializer, DebtPaymentCreateSerializer,
)
from .services import DebtService
from apps.accounts.permissions import IsCashierOrAdmin


class DebtViewSet(viewsets.ReadOnlyModelViewSet):
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'customer']
    search_fields = ['customer__full_name', 'customer__phone']
    ordering_fields = ['due_date', 'remaining_amount', 'created_at']
    ordering = ['-created_at']
    permission_classes = [IsCashierOrAdmin]

    def get_queryset(self):
        return Debt.objects.select_related('customer', 'sale').prefetch_related('payments').all()

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return DebtDetailSerializer
        return DebtListSerializer

    @action(detail=False, methods=['get'])
    def notifications(self, request):
        today = timezone.now().date()
        due_debts_count = Debt.objects.filter(
            due_date__lte=today
        ).exclude(status='PAID').count()

        return Response({
            "success": True,
            "data": {
                "due_debts_count": due_debts_count
            }
        })


class DebtPaymentCreateView(APIView):
    """Process a debt payment."""
    permission_classes = [IsCashierOrAdmin]

    def post(self, request):
        serializer = DebtPaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            debt = Debt.objects.get(pk=serializer.validated_data['debt_id'])
        except Debt.DoesNotExist:
            return Response(
                {"success": False, "message": "Qarz topilmadi.", "errors": {}},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            payment = DebtService.make_payment(
                debt=debt,
                amount=serializer.validated_data['amount'],
                payment_method=serializer.validated_data['payment_method'],
                received_by=request.user,
                notes=serializer.validated_data.get('notes', ''),
            )
        except ValueError as e:
            return Response(
                {"success": False, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            "success": True,
            "message": "To'lov muvaffaqiyatli qabul qilindi.",
            "data": DebtPaymentSerializer(payment).data,
        }, status=status.HTTP_201_CREATED)


class DebtPaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DebtPaymentSerializer
    permission_classes = [IsCashierOrAdmin]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['debt', 'payment_method']
    ordering = ['-created_at']

    def get_queryset(self):
        return DebtPayment.objects.select_related('debt__customer', 'received_by').all()
