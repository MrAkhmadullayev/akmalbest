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

    def get_permissions(self):
        if self.action in ("list", "retrieve", "metadata", "create", "update", "partial_update"):
            return [HasModulePermission()]
        if self.action == "destroy":
            return [HasModulePermission(), IsAdmin()]
        return [HasModulePermission()]

    search_fields = ["name"]


class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    required_module = "expenses"

    def get_permissions(self):
        if self.action in ("list", "retrieve", "metadata", "create", "update", "partial_update"):
            return [HasModulePermission()]
        if self.action == "destroy":
            return [HasModulePermission(), IsAdmin()]
        return [HasModulePermission()]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["category", "expense_date"]
    search_fields = ["title", "description"]
    ordering_fields = ["expense_date", "amount", "created_at"]
    ordering = ["-expense_date"]

    def get_queryset(self):
        # Smena chegarasi apps.reports.shifts dan olinadi — dashboard va
        # Z-hisobot bilan AYNAN bir xil oraliq ishlatilishi shart, aks holda
        # chegaradagi xarajat ro'yxatda ko'rinib, hisobotga tushmay qolardi.
        from apps.reports.shifts import current_shift_start, filter_to_shift

        qs = Expense.objects.select_related("category", "created_by").all()
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        shift_id = self.request.query_params.get("shift_id")

        if shift_id:
            from apps.reports.models import ShiftReport

            try:
                shift = ShiftReport.objects.get(id=shift_id)
            except ShiftReport.DoesNotExist:
                return qs.none()
            return filter_to_shift(qs, shift.opened_at, shift.closed_at)

        if date_from or date_to:
            if date_from:
                qs = qs.filter(expense_date__gte=date_from)
            if date_to:
                qs = qs.filter(expense_date__lte=date_to)
            return qs

        # Standart: faqat joriy smena xarajatlari
        return filter_to_shift(qs, current_shift_start())
