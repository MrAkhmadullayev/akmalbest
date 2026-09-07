"""
Yagona ombor qiymati hisoblash qatlami.

Ilgari dashboard ombor qiymatini partiyalar bo'yicha, ombor hisoboti esa
``current_stock × joriy tannarx`` bo'yicha hisoblardi — natijada bir xil narsa
uchun ikki sahifada ikki xil raqam chiqardi. Endi ikkalasi ham shu yerdan
oladi.

Asos — partiyalar (haqiqiy sotib olingan narx). Partiyaga bog'lanmay qolgan
miqdor (juda eski ma'lumot) mahsulotning joriy tannarxi bo'yicha baholanadi.
"""

from decimal import Decimal

from django.db.models import DecimalField, F, IntegerField, Q, Sum, Value
from django.db.models.functions import Coalesce

from apps.inventory.models import BatchPaymentMethod, InventoryBatch
from apps.products.models import Product

MONEY = DecimalField(max_digits=20, decimal_places=2)
ZERO_MONEY = Value(Decimal("0"), output_field=MONEY)
ZERO_INT = Value(0, output_field=IntegerField())


def _money_sum(expression, condition=None):
    kwargs = {"filter": condition} if condition is not None else {}
    return Coalesce(Sum(expression, output_field=MONEY, **kwargs), ZERO_MONEY)


def stock_valuation(products_qs=None):
    """Return the inventory valuation in a single, consistent shape.

    ``cost_value`` — ombordagi tovarning tannarx bo'yicha qiymati,
    ``retail_value`` — sotish narxi bo'yicha qiymati.

    MUHIM: partiyalar ham, mahsulotlar ham AYNAN bir xil to'plam bo'yicha
    olinadi. Aks holda faol bo'lmagan mahsulotning partiyasi qiymatga
    qo'shilib, dona soni bilan mos kelmay qolardi.
    """
    products_qs = Product.objects.filter(is_active=True) if products_qs is None else products_qs
    product_ids = products_qs.values("pk")

    batch_totals = InventoryBatch.objects.filter(product__in=product_ids, current_quantity__gt=0).aggregate(
        cash=_money_sum(
            F("current_quantity") * F("purchase_price"), Q(payment_method=BatchPaymentMethod.CASH)
        ),
        debt=_money_sum(
            F("current_quantity") * F("purchase_price"), Q(payment_method=BatchPaymentMethod.DEBT)
        ),
        units=Coalesce(Sum("current_quantity"), ZERO_INT),
    )

    product_totals = products_qs.aggregate(
        units=Coalesce(Sum("current_stock"), ZERO_INT),
        cost=_money_sum(F("current_stock") * F("purchase_price")),
        retail=_money_sum(F("current_stock") * F("selling_price")),
    )

    cash_value = batch_totals["cash"]
    debt_value = batch_totals["debt"]
    stock_units = product_totals["units"]

    # Partiyaga bog'lanmagan qoldiq — o'rtacha joriy tannarx bo'yicha.
    # Yaxlitlik saqlanganda bu nolga teng bo'ladi.
    unbatched_units = max(stock_units - batch_totals["units"], 0)
    unbatched_value = Decimal("0")
    if unbatched_units and stock_units:
        unbatched_value = (product_totals["cost"] / stock_units) * unbatched_units

    return {
        "cost_value": cash_value + debt_value + unbatched_value,
        "cash_value": cash_value,
        "debt_value": debt_value,
        "unbatched_units": unbatched_units,
        "unbatched_value": unbatched_value,
        "retail_value": product_totals["retail"],
        "total_units": stock_units,
    }
