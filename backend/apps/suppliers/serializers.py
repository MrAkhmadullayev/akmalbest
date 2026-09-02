"""Supplier serializers."""
from rest_framework import serializers
from .models import Supplier, Purchase, PurchaseItem


class SupplierSerializer(serializers.ModelSerializer):
    total_purchases = serializers.SerializerMethodField()

    class Meta:
        model = Supplier
        fields = [
            'id', 'name', 'contact_person', 'phone', 'address',
            'notes', 'is_active', 'total_purchases', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_total_purchases(self, obj):
        return obj.purchases.count()


class PurchaseItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_barcode = serializers.CharField(source='product.barcode', read_only=True)

    class Meta:
        model = PurchaseItem
        fields = ['id', 'product', 'product_name', 'product_barcode', 'quantity', 'purchase_price', 'payment_method', 'subtotal']
        read_only_fields = ['id', 'subtotal']


class PurchaseSerializer(serializers.ModelSerializer):
    items = PurchaseItemSerializer(many=True, read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True, default='')

    class Meta:
        model = Purchase
        fields = [
            'id', 'supplier', 'supplier_name', 'invoice_number', 'total',
            'status', 'created_by', 'created_by_name',
            'purchase_date', 'notes', 'items', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'total', 'created_by', 'created_at', 'updated_at']


class PurchaseCreateSerializer(serializers.Serializer):
    """Serializer for creating a purchase with items."""
    supplier = serializers.UUIDField()
    invoice_number = serializers.CharField(required=False, allow_blank=True, default='')
    purchase_date = serializers.DateField()
    notes = serializers.CharField(required=False, allow_blank=True, default='')
    items = serializers.ListField(child=serializers.DictField(), min_length=1)

    def validate_items(self, value):
        from apps.products.models import Product
        for item in value:
            if 'product_id' not in item or 'quantity' not in item or 'purchase_price' not in item:
                raise serializers.ValidationError(
                    "Har bir element uchun product_id, quantity va purchase_price kerak."
                )
            try:
                item['product'] = Product.objects.get(pk=item['product_id'])
            except Product.DoesNotExist as err:
                raise serializers.ValidationError(
                    f"Mahsulot topilmadi: {item['product_id']}"
                ) from err
            if int(item['quantity']) < 1:
                raise serializers.ValidationError("Miqdor 1 dan kam bo'lishi mumkin emas.")
        return value
