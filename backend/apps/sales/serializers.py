"""Sale serializers."""

from rest_framework import serializers

from .models import Payment, Sale, SaleItem


class SaleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleItem
        fields = [
            "id",
            "product",
            "product_name_snapshot",
            "barcode_snapshot",
            "purchase_price_snapshot",
            "selling_price_snapshot",
            "quantity",
            "returned_quantity",
            "discount",
            "subtotal",
            "profit",
        ]
        read_only_fields = fields


class PaymentSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True, default="")

    class Meta:
        model = Payment
        fields = ["id", "sale", "amount", "payment_method", "created_by", "created_by_name", "created_at"]
        read_only_fields = fields


class SaleListSerializer(serializers.ModelSerializer):
    cashier_name = serializers.CharField(source="cashier.full_name", read_only=True)
    customer_name = serializers.CharField(source="customer.full_name", read_only=True, default="")
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = [
            "id",
            "sale_number",
            "cashier",
            "cashier_name",
            "customer",
            "customer_name",
            "subtotal",
            "discount",
            "total",
            "profit",
            "payment_method",
            "status",
            "items_count",
            "created_at",
        ]

    def get_items_count(self, obj):
        return obj.items.count()


class SaleDetailSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    cashier_name = serializers.CharField(source="cashier.full_name", read_only=True)
    customer_name = serializers.CharField(source="customer.full_name", read_only=True, default="")
    customer_phone = serializers.CharField(source="customer.phone", read_only=True, default="")

    class Meta:
        model = Sale
        fields = [
            "id",
            "sale_number",
            "cashier",
            "cashier_name",
            "customer",
            "customer_name",
            "customer_phone",
            "subtotal",
            "discount",
            "total",
            "profit",
            "payment_method",
            "status",
            "items",
            "payments",
            "created_at",
            "updated_at",
        ]


class SaleCreateSerializer(serializers.Serializer):
    """Serializer for creating a sale from POS."""

    items = serializers.ListField(child=serializers.DictField(), min_length=1)
    payment_method = serializers.ChoiceField(choices=["CASH", "CARD", "DEBT"])
    customer_id = serializers.UUIDField(required=False, allow_null=True)
    customer_name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    customer_phone = serializers.CharField(required=False, allow_blank=True, max_length=50)
    discount = serializers.DecimalField(max_digits=14, decimal_places=2, required=False, default=0)
    paid_amount = serializers.DecimalField(max_digits=14, decimal_places=2, required=False, allow_null=True)
    due_date = serializers.DateField(required=False, allow_null=True)

    def validate_items(self, value):
        for item in value:
            if "product_id" not in item or "quantity" not in item:
                raise serializers.ValidationError("Har bir element uchun product_id va quantity kerak.")
            if int(item["quantity"]) < 1:
                raise serializers.ValidationError("Miqdor 1 dan kam bo'lishi mumkin emas.")
        return value

    def validate(self, attrs):
        if attrs["payment_method"] == "DEBT":
            if not attrs.get("customer_id") and not attrs.get("customer_name"):
                raise serializers.ValidationError(
                    {"customer_name": "Nasiya savdo uchun mijoz tanlanishi yoki kiritilishi shart."}
                )
            if not attrs.get("due_date"):
                raise serializers.ValidationError({"due_date": "Nasiya savdo uchun muddat kiritilishi shart."})
        return attrs


class SaleReturnSerializer(serializers.Serializer):
    """Serializer for processing a sale return."""

    sale_item_id = serializers.UUIDField()
    return_quantity = serializers.IntegerField(min_value=1)
