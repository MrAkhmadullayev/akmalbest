"""
Smena chegarasini aniqlashning YAGONA joyi.

Ilgari bu mantiq dashboard'da, smena yopishda va xarajatlar ro'yxatida uch
marta takrorlangan edi va chegara turlicha (``>=`` / ``>``) qo'llanardi —
natijada aynan yopilish vaqtidagi yozuv ikki smenaga tushib qolishi mumkin
edi. Endi hamma shu yerdan foydalanadi va chegara EKSKLYUZIV: smenaga
``opened_at < created_at <= closed_at`` oralig'idagi yozuvlar kiradi.
"""

from django.utils import timezone


def current_shift_start(now=None):
    """Ochiq smenaning boshlanish vaqti."""
    from .models import ShiftReport

    now = now or timezone.now()
    last_shift = ShiftReport.objects.order_by("-closed_at").first()
    if last_shift:
        return last_shift.closed_at
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def filter_to_shift(queryset, shift_start, until=None, field="created_at"):
    """Restrict ``queryset`` to the shift window (start exclusive, end inclusive)."""
    queryset = queryset.filter(**{f"{field}__gt": shift_start})
    if until is not None:
        queryset = queryset.filter(**{f"{field}__lte": until})
    return queryset


def shift_querysets(shift_start, until=None):
    """Return (sales, expenses, debt_payments, payments) for the shift window.

    ``payments`` — kassa harakati uchun. U savdolardan alohida olinadi, chunki
    qaytarim savdo qilingan smenada emas, pul chiqqan smenada hisoblanishi
    kerak.
    """
    from apps.debts.models import DebtPayment
    from apps.expenses.models import Expense
    from apps.sales.models import Payment, Sale

    return (
        filter_to_shift(Sale.objects.all(), shift_start, until),
        filter_to_shift(Expense.objects.all(), shift_start, until),
        filter_to_shift(DebtPayment.objects.all(), shift_start, until),
        filter_to_shift(Payment.objects.all(), shift_start, until),
    )
