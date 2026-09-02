"""
Inventory serializers.
"""
from rest_framework import serializers
from .models import Inventory, InventoryTransaction


class InventorySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_barcode = serializers.CharField(source='product.barcode', read_only=True)
    stock_status = serializers.CharField(source='product.stock_status', read_only=True)

    class Meta:
        model = Inventory
        fields = [
            'id', 'product', 'product_name', 'product_barcode',
            'quantity', 'stock_status', 'updated_at',
        ]
        read_only_fields = ['id', 'updated_at']


class InventoryAdjustSerializer(serializers.Serializer):
    """Serializer for manual inventory adjustments."""
    product_id = serializers.UUIDField()
    new_quantity = serializers.IntegerField(min_value=0)
    notes = serializers.CharField(required=False, allow_blank=True, default='')


class InventoryTransactionSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_barcode = serializers.CharField(source='product.barcode', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True, default='')

    class Meta:
        model = InventoryTransaction
        fields = [
            'id', 'product', 'product_name', 'product_barcode',
            'transaction_type', 'quantity', 'previous_quantity', 'new_quantity',
            'reference_id', 'reference_type',
            'created_by', 'created_by_name', 'notes', 'created_at',
        ]
        read_only_fields = fields
