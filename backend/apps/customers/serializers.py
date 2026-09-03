"""Customer serializers."""

from django.db.models import Sum
from rest_framework import serializers

from .models import Customer


class CustomerSerializer(serializers.ModelSerializer):
    total_debt = serializers.SerializerMethodField()
    total_purchases = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            "id",
            "full_name",
            "phone",
            "address",
            "notes",
            "is_active",
            "total_debt",
            "total_purchases",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_total_debt(self, obj):
        from apps.debts.models import Debt

        result = Debt.objects.filter(customer=obj).exclude(status="PAID").aggregate(total=Sum("remaining_amount"))
        return str(result["total"] or 0)

    def get_total_purchases(self, obj):
        return obj.sales.count() if hasattr(obj, "sales") else 0


class CustomerDetailSerializer(CustomerSerializer):
    total_paid = serializers.SerializerMethodField()

    class Meta(CustomerSerializer.Meta):
        fields = CustomerSerializer.Meta.fields + ["total_paid"]

    def get_total_paid(self, obj):
        from apps.debts.models import Debt

        result = Debt.objects.filter(customer=obj).aggregate(total=Sum("paid_amount"))
        return str(result["total"] or 0)
