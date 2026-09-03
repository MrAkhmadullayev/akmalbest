"""Reports serializers."""
from rest_framework import serializers
from .models import ShiftReport

class ShiftReportSerializer(serializers.ModelSerializer):
    closed_by_name = serializers.CharField(source='closed_by.full_name', read_only=True, default='')

    class Meta:
        model = ShiftReport
        fields = [
            'id', 'shift_number', 'opened_at', 'closed_at', 'closed_by', 'closed_by_name',
            'total_sales', 'total_cash', 'total_card', 'total_debt',
            'total_profit', 'total_expenses', 'sales_count'
        ]
        read_only_fields = fields
