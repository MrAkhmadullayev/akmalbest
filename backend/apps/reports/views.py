"""Reports views - analytics and dashboard data from real database.

Muhim qoida: tushum/foyda hech qachon shu yerda qo'lda yig'ilmaydi —
``apps.sales.finance`` va ``apps.inventory.valuation`` modullaridan olinadi.
Shunda dashboard, smena hisoboti va hisobotlar sahifasi bir xil raqam
ko'rsatadi.
"""

from decimal import Decimal

from django.db.models import Count, F, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasModulePermission
from apps.debts.models import Debt, DebtStatus
from apps.expenses.models import Expense
from apps.inventory.models import Inventory
from apps.inventory.valuation import stock_valuation
from apps.products.models import Product
from apps.sales.finance import aggregate_sales, cash_movement, revenue_queryset
from apps.sales.models import Sale, SaleItem

from .models import ShiftReport
from .serializers import ShiftReportSerializer
from .shifts import current_shift_start, shift_querysets

__all__ = [
    "current_shift_start",
    "shift_querysets",
    "DashboardView",
    "CloseShiftView",
    "ShiftListView",
    "SalesReportView",
    "ProfitReportView",
    "InventoryReportView",
    "DebtReportView",
]


class DashboardView(APIView):
    """Dashboard statistics - all data from database."""

    required_module = "dashboard"
    permission_classes = [HasModulePermission]

    def get(self, request):
        shift_start = current_shift_start()
        shift_sales, shift_expenses, shift_debt_payments, shift_payments = shift_querysets(shift_start)

        summary = aggregate_sales(shift_sales)
        cash = cash_movement(shift_payments, shift_debt_payments, shift_expenses)

        # Debts
        total_debt = Debt.objects.exclude(status=DebtStatus.PAID).aggregate(total=Sum("remaining_amount"))[
            "total"
        ] or Decimal("0")

        overdue_debt = Debt.objects.filter(status=DebtStatus.OVERDUE).aggregate(total=Sum("remaining_amount"))[
            "total"
        ] or Decimal("0")

        overdue_count = Debt.objects.filter(status=DebtStatus.OVERDUE).count()

        # Stock — yagona manba: Inventory.quantity
        low_stock_count = Inventory.objects.filter(
            product__is_active=True, quantity__lte=F("product__min_stock"), quantity__gt=0
        ).count()
        out_of_stock_count = Inventory.objects.filter(product__is_active=True, quantity__lte=0).count()
        total_products = Product.objects.filter(is_active=True).count()

        valuation = stock_valuation()

        # Recent sales
        recent_sales = Sale.objects.select_related("cashier", "customer").order_by("-created_at")[:10]
        recent_sales_data = [
            {
                "id": str(s.id),
                "sale_number": s.sale_number,
                "cashier": s.cashier.full_name,
                "customer": s.customer.full_name if s.customer else "",
                "total": str(s.total),
                "net_total": str(s.net_total),
                "payment_method": s.payment_method,
                "status": s.status,
                "created_at": s.created_at.isoformat(),
            }
            for s in recent_sales
        ]

        # Low stock products
        low_stock_rows = (
            Inventory.objects.select_related("product")
            .filter(product__is_active=True, quantity__lte=F("product__warning_stock"))
            .order_by("quantity")[:10]
        )
        low_stock_data = [
            {
                "id": str(inv.product.id),
                "name": inv.product.name,
                "barcode": inv.product.barcode,
                "current_stock": inv.quantity,
                "min_stock": inv.product.min_stock,
                "stock_status": inv.stock_status,
            }
            for inv in low_stock_rows
        ]

        # Overdue debts
        overdue_debts = (
            Debt.objects.filter(status=DebtStatus.OVERDUE).select_related("customer").order_by("due_date")[:10]
        )
        overdue_data = [
            {
                "id": str(d.id),
                "customer": d.customer.full_name,
                "phone": d.customer.phone,
                "remaining_amount": str(d.remaining_amount),
                "due_date": str(d.due_date),
            }
            for d in overdue_debts
        ]

        return Response(
            {
                "shift_started_at": shift_start.isoformat(),
                "today_sales_total": str(summary["total_sales"]),
                "today_sales_count": summary["sales_count"],
                # Naqd/karta — kassaga haqiqatan kirgan pul (qaytarimlar ayirilgan).
                "today_cash_sales": str(cash["cash_sales"]),
                "today_card_sales": str(cash["card_sales"]),
                "today_debt_sales": str(summary["debt_sales"]),
                "today_profit": str(summary["total_profit"]),
                "today_returns": str(summary["returned_total"]),
                "today_expenses": str(cash["expenses"]),
                "today_refunds_cash": str(cash["refunds_cash"]),
                "today_debt_payments_cash": str(cash["debt_payments_cash"]),
                "today_debt_payments_card": str(cash["debt_payments_card"]),
                "expected_cash": str(cash["expected_cash"]),
                "total_debt": str(total_debt),
                "overdue_debt": str(overdue_debt),
                "overdue_count": overdue_count,
                "low_stock_count": low_stock_count,
                "out_of_stock_count": out_of_stock_count,
                "total_products": total_products,
                "inventory_debt_value": str(valuation["debt_value"]),
                "inventory_cash_value": str(valuation["cash_value"]),
                "inventory_total_value": str(valuation["cost_value"]),
                "recent_sales": recent_sales_data,
                "low_stock_products": low_stock_data,
                "overdue_debts": overdue_data,
            }
        )


class CloseShiftView(APIView):
    """Close the current shift and generate a Z-Report."""

    required_module = "dashboard"
    permission_classes = [HasModulePermission]

    def post(self, request):
        now = timezone.now()
        shift_start = current_shift_start(now)
        shift_sales, shift_expenses, shift_debt_payments, shift_payments = shift_querysets(shift_start, until=now)

        summary = aggregate_sales(shift_sales)
        cash = cash_movement(shift_payments, shift_debt_payments, shift_expenses)

        has_activity = (
            summary["sales_count"] > 0
            or cash["expenses"] > 0
            or cash["debt_payments_cash"] > 0
            or cash["debt_payments_card"] > 0
        )
        if not has_activity:
            return Response({"success": False, "message": "Smenada hech qanday tranzaksiya yo'q!"}, status=400)

        # Smena raqami: YYYYMMDD-XX
        prefix = now.strftime("%Y%m%d")
        last_num_today = ShiftReport.objects.filter(shift_number__startswith=prefix).count()
        shift_number = f"{prefix}-{(last_num_today + 1):02d}"

        report = ShiftReport.objects.create(
            shift_number=shift_number,
            opened_at=shift_start,
            closed_by=request.user,
            total_sales=summary["total_sales"],
            # Naqd/karta — haqiqiy kassa harakati bo'yicha (qaytarimlar ayirilgan).
            total_cash=cash["cash_sales"],
            total_card=cash["card_sales"],
            total_debt=summary["debt_sales"],
            total_profit=summary["total_profit"],
            total_expenses=cash["expenses"],
            total_returns=summary["returned_total"],
            total_debt_payments_cash=cash["debt_payments_cash"],
            total_debt_payments_card=cash["debt_payments_card"],
            expected_cash=cash["expected_cash"],
            sales_count=summary["sales_count"],
        )

        return Response(
            {"success": True, "message": "Smena muvaffaqiyatli yopildi.", "data": ShiftReportSerializer(report).data}
        )


class ShiftListView(APIView):
    """List all closed shifts."""

    required_module = "reports"
    permission_classes = [HasModulePermission]

    def get(self, request):
        shifts = ShiftReport.objects.all().select_related("closed_by")
        serializer = ShiftReportSerializer(shifts, many=True)
        return Response({"results": serializer.data})


class SalesReportView(APIView):
    """Sales report with date range filtering."""

    required_module = "reports"
    permission_classes = [HasModulePermission]

    def get(self, request):
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        qs = revenue_queryset()
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        summary = aggregate_sales(qs)
        total_discount = qs.aggregate(t=Sum("discount"))["t"] or Decimal("0")

        # Savdo turi bo'yicha — sof qiymatda.
        # Diqqat: annotate kaliti model maydoni bilan bir xil bo'lmasligi kerak
        # (`total=Sum(F("total")...)` -> "'total' is an aggregate" xatosi).
        by_method = [
            {"payment_method": row["payment_method"], "count": row["count"], "total": row["net_amount"]}
            for row in qs.values("payment_method").annotate(
                count=Count("id"), net_amount=Sum(F("total") - F("returned_total"))
            )
        ]

        # Kunlar kesimida — sof qiymatda
        daily = [
            {
                "day": row["day"],
                "total": row["net_amount"],
                "profit": row["net_gain"],
                "count": row["count"],
            }
            for row in qs.annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(
                net_amount=Sum(F("total") - F("returned_total")),
                net_gain=Sum(F("profit") - F("returned_profit")),
                count=Count("id"),
            )
            .order_by("day")
        ]

        # Top mahsulotlar — qaytarilgani ayirilgan holda
        top_products = list(
            SaleItem.objects.filter(sale__in=qs)
            .values("product__name", "product__barcode")
            .annotate(
                total_qty=Sum(F("quantity") - F("returned_quantity")),
                total_revenue=Sum(F("subtotal") - F("returned_subtotal")),
                total_profit=Sum(F("profit") - F("returned_profit")),
            )
            .order_by("-total_qty")[:10]
        )

        return Response(
            {
                "summary": {
                    "total_revenue": str(summary["total_sales"]),
                    "gross_revenue": str(summary["gross_sales"]),
                    "total_returns": str(summary["returned_total"]),
                    "total_profit": str(summary["total_profit"]),
                    "total_sales": summary["sales_count"],
                    "total_discount": str(total_discount),
                },
                "by_payment_method": by_method,
                "daily": daily,
                "top_products": top_products,
            }
        )


class ProfitReportView(APIView):
    """Profit report."""

    required_module = "reports"
    permission_classes = [HasModulePermission]

    def get(self, request):
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        sales_qs = revenue_queryset()
        expenses_qs = Expense.objects.all()

        # Ikkala tomon ham bir xil kalendar sanasi bo'yicha filtrlanadi.
        if date_from:
            sales_qs = sales_qs.filter(created_at__date__gte=date_from)
            expenses_qs = expenses_qs.filter(expense_date__gte=date_from)
        if date_to:
            sales_qs = sales_qs.filter(created_at__date__lte=date_to)
            expenses_qs = expenses_qs.filter(expense_date__lte=date_to)

        summary = aggregate_sales(sales_qs)
        total_expenses = expenses_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0")
        net_profit = summary["total_profit"] - total_expenses

        return Response(
            {
                "revenue": str(summary["total_sales"]),
                "gross_profit": str(summary["total_profit"]),
                "total_returns": str(summary["returned_total"]),
                "total_expenses": str(total_expenses),
                "net_profit": str(net_profit),
            }
        )


class InventoryReportView(APIView):
    """Inventory report."""

    required_module = "reports"
    permission_classes = [HasModulePermission]

    def get(self, request):
        products = Product.objects.filter(is_active=True)
        valuation = stock_valuation(products)

        low_stock = Inventory.objects.filter(
            product__is_active=True, quantity__lte=F("product__min_stock"), quantity__gt=0
        ).count()
        out_of_stock = Inventory.objects.filter(product__is_active=True, quantity__lte=0).count()

        return Response(
            {
                "total_products": products.count(),
                "total_units": valuation["total_units"],
                # Dashboard bilan bir xil formula (partiya narxlari bo'yicha).
                "total_stock_value": str(valuation["cost_value"]),
                "stock_value_cash": str(valuation["cash_value"]),
                "stock_value_debt": str(valuation["debt_value"]),
                "total_retail_value": str(valuation["retail_value"]),
                "low_stock_count": low_stock,
                "out_of_stock_count": out_of_stock,
            }
        )


class DebtReportView(APIView):
    """Debt report."""

    required_module = "reports"
    permission_classes = [HasModulePermission]

    def get(self, request):
        debts = Debt.objects.exclude(status=DebtStatus.PAID)

        total_debt = debts.aggregate(total=Sum("remaining_amount"))["total"] or Decimal("0")
        active_count = debts.filter(status=DebtStatus.ACTIVE).count()
        overdue_count = debts.filter(status=DebtStatus.OVERDUE).count()
        partially_paid = debts.filter(status=DebtStatus.PARTIALLY_PAID).count()

        from apps.customers.models import Customer

        top_debtors = (
            Customer.objects.filter(
                debts__status__in=[DebtStatus.ACTIVE, DebtStatus.PARTIALLY_PAID, DebtStatus.OVERDUE]
            )
            .annotate(total_remaining=Sum("debts__remaining_amount"))
            .order_by("-total_remaining")[:10]
        )

        top_debtors_data = [
            {
                "id": str(c.id),
                "name": c.full_name,
                "phone": c.phone,
                "total_remaining": str(c.total_remaining),
            }
            for c in top_debtors
        ]

        return Response(
            {
                "total_debt": str(total_debt),
                "active_count": active_count,
                "overdue_count": overdue_count,
                "partially_paid_count": partially_paid,
                "top_debtors": top_debtors_data,
            }
        )
