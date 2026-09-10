"""
Bitta smena ichidagi harakatlarni turlar bo'yicha ochib beradi.

Smenalar tarixi sahifasidagi kartalar (Jami savdo, Sof foyda, Naqd, Karta,
Nasiya, Xarajatlar, Qarz to'lovlari, Qaytarimlar) shu endpointdan
foydalanadi: kartaga bosilganda o'sha smenada AYNAN nima bo'lganini
ko'rsatadi.

    GET /api/reports/shifts/<uuid>/details/?kind=expenses

Smena oralig'i `apps.reports.shifts.filter_to_shift` orqali olinadi —
Z-hisobot qanday hisoblagan bo'lsa, ro'yxat ham xuddi shunday chiqadi.
"""

from decimal import Decimal

from django.db.models import Sum
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasModulePermission
from apps.debts.models import DebtPayment
from apps.expenses.models import Expense
from apps.sales.finance import revenue_queryset
from apps.sales.models import Payment, PaymentMethod, Sale

from .models import ShiftReport
from .shifts import filter_to_shift

KINDS = (
    "sales",
    "profit",
    "cash",
    "card",
    "debt",
    "expenses",
    "debt_payments",
    "debt_payments_cash",
    "debt_payments_card",
    "returns",
)


def _sale_row(sale):
    return {
        "id": str(sale.id),
        "title": f"Savdo #{sale.sale_number}",
        "subtitle": sale.customer.full_name if sale.customer else "",
        "person": sale.cashier.full_name if sale.cashier else "",
        "amount": str(sale.net_total),
        "extra": str(sale.net_profit),
        "method": sale.payment_method,
        "status": sale.status,
        "created_at": sale.created_at.isoformat(),
        "link": f"/sales/{sale.id}",
    }


def _sales_queryset(window):
    return revenue_queryset(window).select_related("cashier", "customer").order_by("-created_at")


class ShiftDetailView(APIView):
    """Smenadagi harakatlar ro'yxati (kartalar uchun)."""

    required_module = "reports"
    permission_classes = [HasModulePermission]

    def get(self, request, shift_id):
        kind = request.query_params.get("kind", "sales")
        if kind not in KINDS:
            return Response(
                {"success": False, "message": f"Noma'lum tur: {kind}", "errors": {}}, status=400
            )

        try:
            shift = ShiftReport.objects.get(pk=shift_id)
        except ShiftReport.DoesNotExist:
            return Response({"success": False, "message": "Smena topilmadi.", "errors": {}}, status=404)

        start, end = shift.opened_at, shift.closed_at
        handler = getattr(self, f"_kind_{kind}")
        rows, total, label = handler(start, end)

        return Response(
            {
                "shift_number": shift.shift_number,
                "kind": kind,
                "label": label,
                "opened_at": start.isoformat(),
                "closed_at": end.isoformat(),
                "count": len(rows),
                "total": str(total),
                "results": rows,
            }
        )

    # ------------------------------------------------------------------
    # Savdolar
    # ------------------------------------------------------------------

    def _kind_sales(self, start, end):
        qs = _sales_queryset(filter_to_shift(Sale.objects.all(), start, end))
        rows = [_sale_row(s) for s in qs]
        total = sum((s.net_total for s in qs), Decimal("0"))
        return rows, total, "Smenadagi savdolar"

    def _kind_profit(self, start, end):
        qs = _sales_queryset(filter_to_shift(Sale.objects.all(), start, end))
        rows = sorted((_sale_row(s) for s in qs), key=lambda r: Decimal(r["extra"]), reverse=True)
        total = sum((s.net_profit for s in qs), Decimal("0"))
        return rows, total, "Foyda bo'yicha savdolar"

    def _kind_by_method(self, start, end, method, label):
        qs = _sales_queryset(filter_to_shift(Sale.objects.all(), start, end)).filter(payment_method=method)
        rows = [_sale_row(s) for s in qs]
        total = sum((s.net_total for s in qs), Decimal("0"))
        return rows, total, label

    def _kind_payments(self, start, end, method, label):
        """Kassa harakati — `Payment` yozuvlari bo'yicha.

        MUHIM: Z-hisobotdagi "Naqd/Karta tushum" ham aynan shu manbadan
        hisoblanadi (`cash_movement`). Agar bu yerda savdolar ro'yxatlansa,
        kartadagi summa bilan ro'yxatning jami summasi mos kelmay qolardi —
        qaytarimlar va boshqa smenada qaytarilgan savdolar farq beradi.
        """
        qs = (
            filter_to_shift(Payment.objects.filter(payment_method=method), start, end)
            .select_related("sale", "sale__customer", "created_by")
            .order_by("-created_at")
        )
        rows = []
        total = Decimal("0")
        for p in qs:
            refund = p.is_refund
            total += -p.amount if refund else p.amount
            rows.append(
                {
                    "id": str(p.id),
                    "title": (
                        f"{'Qaytarim' if refund else 'To\'lov'} — Savdo #{p.sale.sale_number}"
                        if p.sale
                        else ("Qaytarim" if refund else "To'lov")
                    ),
                    "subtitle": p.sale.customer.full_name if p.sale and p.sale.customer else "",
                    "person": p.created_by.full_name if p.created_by else "",
                    "amount": str(-p.amount if refund else p.amount),
                    "extra": "",
                    "method": p.payment_method,
                    "status": "REFUND" if refund else "PAYMENT",
                    "created_at": p.created_at.isoformat(),
                    "link": f"/sales/{p.sale_id}" if p.sale_id else "",
                }
            )
        return rows, total, label

    def _kind_cash(self, start, end):
        return self._kind_payments(start, end, PaymentMethod.CASH, "Naqd kassa harakati")

    def _kind_card(self, start, end):
        return self._kind_payments(start, end, PaymentMethod.CARD, "Karta orqali tushumlar")

    def _kind_debt(self, start, end):
        return self._kind_by_method(start, end, PaymentMethod.DEBT, "Nasiya savdolar")

    # ------------------------------------------------------------------
    # Xarajatlar
    # ------------------------------------------------------------------

    def _kind_expenses(self, start, end):
        qs = (
            filter_to_shift(Expense.objects.all(), start, end)
            .select_related("category", "created_by")
            .order_by("-created_at")
        )
        rows = [
            {
                "id": str(e.id),
                "title": e.title,
                "subtitle": e.category.name if e.category else "Kategoriyasiz",
                "person": e.created_by.full_name if e.created_by else "",
                "amount": str(e.amount),
                "extra": e.description or "",
                "created_at": e.created_at.isoformat(),
                "link": "",
            }
            for e in qs
        ]
        total = qs.aggregate(t=Sum("amount"))["t"] or Decimal("0")
        return rows, total, "Smenadagi xarajatlar"

    # ------------------------------------------------------------------
    # Qarz to'lovlari
    # ------------------------------------------------------------------

    def _kind_debt_payments(self, start, end, method=None, label=None):
        qs = (
            filter_to_shift(DebtPayment.objects.all(), start, end)
            .select_related("debt__customer", "received_by")
            .order_by("-created_at")
        )
        if method:
            qs = qs.filter(payment_method=method)
        rows = [
            {
                "id": str(p.id),
                "title": p.debt.customer.full_name if p.debt and p.debt.customer else "Qarz to'lovi",
                "subtitle": "Naqd" if p.payment_method == "CASH" else "Karta",
                "person": p.received_by.full_name if p.received_by else "",
                "amount": str(p.amount),
                "extra": p.notes or "",
                "method": p.payment_method,
                "created_at": p.created_at.isoformat(),
                "link": f"/debts?customer={p.debt.customer_id}" if p.debt else "",
            }
            for p in qs
        ]
        total = qs.aggregate(t=Sum("amount"))["t"] or Decimal("0")
        return rows, total, label or "Smenadagi qarz to'lovlari"

    def _kind_debt_payments_cash(self, start, end):
        return self._kind_debt_payments(start, end, "CASH", "Qarz to'lovlari — naqd")

    def _kind_debt_payments_card(self, start, end):
        return self._kind_debt_payments(start, end, "CARD", "Qarz to'lovlari — karta")

    # ------------------------------------------------------------------
    # Qaytarimlar
    # ------------------------------------------------------------------

    def _kind_returns(self, start, end):
        """Qaytarilgan savdolar.

        Z-hisobotdagi `total_returns` shu smenada QILINGAN savdolarning
        qaytarilgan qismidan yig'iladi, shuning uchun ro'yxat ham xuddi
        shu asosda tuziladi — aks holda kartadagi summa bilan mos kelmasdi.
        """
        qs = _sales_queryset(filter_to_shift(Sale.objects.all(), start, end)).exclude(returned_total=0)
        rows = []
        total = Decimal("0")
        for sale in qs:
            total += sale.returned_total
            rows.append(
                {
                    "id": str(sale.id),
                    "title": f"Savdo #{sale.sale_number}",
                    "subtitle": sale.customer.full_name if sale.customer else "",
                    "person": sale.cashier.full_name if sale.cashier else "",
                    "amount": str(sale.returned_total),
                    "extra": str(sale.total),
                    "method": sale.payment_method,
                    "status": sale.status,
                    "created_at": sale.created_at.isoformat(),
                    "link": f"/sales/{sale.id}",
                }
            )
        return rows, total, "Qaytarilgan savdolar"
