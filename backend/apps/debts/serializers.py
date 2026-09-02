"""Debt serializers."""
from rest_framework import serializers

from .models import Debt, DebtPayment


class DebtPaymentSerializer(serializers.ModelSerializer):
    received_by_name = serializers.CharField(source='received_by.full_name', read_only=True, default='')

    class Meta:
        model = DebtPayment
        fields = ['id', 'debt', 'amount', 'payment_method', 'received_by', 'received_by_name', 'notes', 'created_at']
        read_only_fields = ['id', 'created_at']


class DebtListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone', read_only=True, default='')
    sale_number = serializers.CharField(source='sale.sale_number', read_only=True, default='')

    class Meta:
        model = Debt
        fields = [
            'id', 'customer', 'customer_name', 'customer_phone',
            'sale', 'sale_number', 'original_amount', 'paid_amount',
            'remaining_amount', 'debt_date', 'due_date', 'status',
            'notes', 'created_at',
        ]


class DebtDetailSerializer(DebtListSerializer):
    payments = DebtPaymentSerializer(many=True, read_only=True)

    class Meta(DebtListSerializer.Meta):
        fields = DebtListSerializer.Meta.fields + ['payments', 'updated_at']


class DebtPaymentCreateSerializer(serializers.Serializer):
    debt_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0.01)
    payment_method = serializers.ChoiceField(choices=['CASH', 'CARD'])
    notes = serializers.CharField(required=False, allow_blank=True, default='')
