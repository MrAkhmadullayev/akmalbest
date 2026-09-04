"""Expense views."""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from apps.accounts.permissions import HasModulePermission, IsAdmin

from .models import Expense, ExpenseCategory
from .serializers import ExpenseCategorySerializer, ExpenseSerializer


class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    queryset = ExpenseCategory.objects.all()
    serializer_class = ExpenseCategorySerializer
    required_module = "expenses"
    permission_classes = [HasModulePermission, IsAdmin]
    search_fields = ["name"]


class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    required_module = "expenses"
    permission_classes = [HasModulePermission, IsAdmin]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["category", "expense_date"]
    search_fields = ["title", "description"]
    ordering_fields = ["expense_date", "amount", "created_at"]
    ordering = ["-expense_date"]

    def get_queryset(self):
        qs = Expense.objects.select_related("category", "created_by").all()
        # Date range filtering
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        shift_id = self.request.query_params.get("shift_id")
        
        if shift_id:
            # Get expenses for a specific shift
            from apps.reports.models import ShiftReport
            try:
                shift = ShiftReport.objects.get(id=shift_id)
                qs = qs.filter(created_at__gte=shift.opened_at, created_at__lte=shift.closed_at)
            except ShiftReport.DoesNotExist:
                qs = qs.none()
            return qs

        if date_from or date_to:
            if date_from:
                qs = qs.filter(expense_date__gte=date_from)
            if date_to:
                qs = qs.filter(expense_date__lte=date_to)
        else:
            # Default: only current shift expenses
            from apps.reports.models import ShiftReport
            from django.utils import timezone
            
            last_shift = ShiftReport.objects.order_by("-closed_at").first()
            if last_shift:
                shift_start = last_shift.closed_at
            else:
                shift_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            qs = qs.filter(created_at__gte=shift_start)
            
        return qs
