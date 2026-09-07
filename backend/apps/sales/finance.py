"""
Yagona moliya hisoblash qatlami.

Butun tizim bo'ylab tushum/foyda BIR joyda hisoblanadi. Ilgari har bir view
o'zicha `status=COMPLETED` filtri bilan yig'ardi va natijada:
  * qisman qaytarilgan savdo hisobotdan BUTUNLAY tushib qolardi,
  * savdolar ro'yxatida bekor qilinganlar to'liq summasi bilan qo'shilardi.

Qoidalar:
  * Bekor qilingan savdo (CANCELLED) tushumga kirmaydi.
  * Qolgan savdolar SOF qiymat bilan kiradi: ``total - returned_total``.
"""

from decimal import Decimal

from django.db.models import Count, DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce

from .models import PaymentMethod, Sale, SaleStatus

MONEY = DecimalField(max_digits=20, decimal_places=2)
ZERO = Value(Decimal("0"), output_field=MONEY)


# Sof qiymat ifodalari. Funksiya ko'rinishida — har chaqiruvda YANGI obyekt
# qaytadi. Bitta ifoda obyektini bir nechta agregatda qayta ishlatish Django'da
# kutilmagan holatlarga olib keladi.
def net_total_expr():
    return F("total") - F("returned_total")


def net_profit_expr():
    return F("profit") - F("returned_profit")


def revenue_queryset(qs=None):
    """Savdolarning tushumga kiradigan qismi (bekor qilinganlarsiz)."""
    qs = Sale.objects.all() if qs is None else qs
    return qs.exclude(status=SaleStatus.CANCELLED)


def _money_sum(expression, condition=None):
    """Coalesce'langan pul yig'indisi, tipi aniq belgilangan holda."""
    kwargs = {"filter": condition} if condition is not None else {}
    return Coalesce(Sum(expression, output_field=MONEY, **kwargs), ZERO)


def net_revenue(qs):
    """Sof tushum: Σ(total) − Σ(returned_total)."""
    return revenue_queryset(qs).aggregate(t=_money_sum(net_total_expr()))["t"]


def net_profit(qs):
    """Sof foyda: Σ(profit) − Σ(returned_profit)."""
    return revenue_queryset(qs).aggregate(t=_money_sum(net_profit_expr()))["t"]


def aggregate_sales(qs=None):
    """Return the standard revenue summary for a set of sales.

    Barcha sahifalar shu funksiyadan foydalanadi — raqamlar bir xil bo'lishi
    kafolatlanadi. Hammasi BITTA so'rovda hisoblanadi.

    Diqqat: agregat kalitlari model maydon nomlari bilan bir xil BO'LMASLIGI
    kerak. `returned_total=Sum(...)` deb nomlansa, Django keyingi
    `F("returned_total")` ni maydon emas, o'sha agregat deb talqin qiladi va
    "'returned_total' is an aggregate" xatosini beradi. Shuning uchun ichkarida
    `_returned_sum` nomi ishlatiladi.
    """
    qs = revenue_queryset(qs)

    raw = qs.aggregate(
        _net_total=_money_sum(net_total_expr()),
        _gross_total=_money_sum(F("total")),
        _returned_sum=_money_sum(F("returned_total")),
        _net_profit=_money_sum(net_profit_expr()),
        _cash=_money_sum(net_total_expr(), Q(payment_method=PaymentMethod.CASH)),
        _card=_money_sum(net_total_expr(), Q(payment_method=PaymentMethod.CARD)),
        _debt=_money_sum(net_total_expr(), Q(payment_method=PaymentMethod.DEBT)),
        _count=Count("id"),
    )

    return {
        "total_sales": raw["_net_total"],
        "gross_sales": raw["_gross_total"],
        "returned_total": raw["_returned_sum"],
        "total_profit": raw["_net_profit"],
        "cash_sales": raw["_cash"],
        "card_sales": raw["_card"],
        "debt_sales": raw["_debt"],
        "sales_count": raw["_count"],
    }


def _sum_amount(qs, condition=None):
    return qs.aggregate(t=_money_sum(F("amount"), condition))["t"]


def cash_movement(payments_qs=None, debt_payments_qs=None, expenses_qs=None):
    """Kassa harakati — HAQIQIY to'lov yozuvlari bo'yicha.

    Muhim: kassa savdolar jadvalidan emas, ``Payment`` yozuvlaridan
    hisoblanadi. Sabab — pul harakati va savdo sanasi mos kelmasligi mumkin:
    kecha qilingan savdo bugun qaytarilsa, pul BUGUN kassadan chiqadi.
    ``Payment.created_at`` shuni to'g'ri joylashtiradi.

    Ilgari smena kassasi faqat ``Sale.payment_method="CASH"`` dan yig'ilardi;
    nasiya to'lovlari ham, qaytarimlar ham hisobga olinmasdi — shuning uchun
    kassa hech qachon to'g'ri kelmasdi.
    """
    cash_in = cash_out = card_in = card_out = Decimal("0")

    if payments_qs is not None:
        totals = payments_qs.aggregate(
            _cash_in=_money_sum(F("amount"), Q(payment_method=PaymentMethod.CASH, is_refund=False)),
            _cash_out=_money_sum(F("amount"), Q(payment_method=PaymentMethod.CASH, is_refund=True)),
            _card_in=_money_sum(F("amount"), Q(payment_method=PaymentMethod.CARD, is_refund=False)),
            _card_out=_money_sum(F("amount"), Q(payment_method=PaymentMethod.CARD, is_refund=True)),
        )
        cash_in, cash_out = totals["_cash_in"], totals["_cash_out"]
        card_in, card_out = totals["_card_in"], totals["_card_out"]

    debt_cash = Decimal("0")
    debt_card = Decimal("0")
    if debt_payments_qs is not None:
        debt_totals = debt_payments_qs.aggregate(
            _cash=_money_sum(F("amount"), Q(payment_method="CASH")),
            _card=_money_sum(F("amount"), Q(payment_method="CARD")),
        )
        debt_cash, debt_card = debt_totals["_cash"], debt_totals["_card"]

    expenses = Decimal("0")
    if expenses_qs is not None:
        expenses = _sum_amount(expenses_qs)

    cash_sales = cash_in - cash_out
    card_sales = card_in - card_out

    return {
        "cash_sales": cash_sales,
        "card_sales": card_sales,
        "refunds_cash": cash_out,
        "refunds_card": card_out,
        "debt_payments_cash": debt_cash,
        "debt_payments_card": debt_card,
        "expenses": expenses,
        # Smena oxirida kassada bo'lishi kerak bo'lgan naqd pul.
        "expected_cash": cash_sales + debt_cash - expenses,
    }
