"""
Qaytarishlarni pul jihatdan to'g'ri hisoblash uchun maydonlar.

Ilgari qaytarilgan savdo hisobotlarda ``status=COMPLETED`` filtri tufayli
BUTUNLAY yo'qolib ketardi. Endi asl hujjat o'zgarmaydi, qaytarilgan qism
alohida saqlanadi va sof qiymat shundan chiqariladi.
"""

from decimal import Decimal

from django.db import migrations, models


def backfill_returns(apps, schema_editor):
    """Mavjud qaytarishlar uchun pul qiymatlarini proporsional to'ldiradi."""
    Sale = apps.get_model("sales", "Sale")
    SaleItem = apps.get_model("sales", "SaleItem")
    db = schema_editor.connection.alias

    touched_sales = set()

    for item in SaleItem.objects.using(db).filter(returned_quantity__gt=0).iterator():
        if item.quantity <= 0:
            continue

        if item.returned_quantity >= item.quantity:
            item.returned_subtotal = item.subtotal
            item.returned_cogs_cash = item.cogs_cash
            item.returned_cogs_debt = item.cogs_debt
            item.returned_profit = item.profit
        else:
            ratio = Decimal(item.returned_quantity) / Decimal(item.quantity)
            item.returned_subtotal = (item.subtotal * ratio).quantize(Decimal("0.01"))
            item.returned_cogs_cash = (item.cogs_cash * ratio).quantize(Decimal("0.01"))
            item.returned_cogs_debt = (item.cogs_debt * ratio).quantize(Decimal("0.01"))
            item.returned_profit = (
                item.returned_subtotal - (item.returned_cogs_cash + item.returned_cogs_debt)
            ).quantize(Decimal("0.01"))

        item.save(
            update_fields=[
                "returned_subtotal",
                "returned_cogs_cash",
                "returned_cogs_debt",
                "returned_profit",
            ]
        )
        touched_sales.add(item.sale_id)

    for sale in Sale.objects.using(db).filter(pk__in=touched_sales).iterator():
        items = list(SaleItem.objects.using(db).filter(sale=sale))
        sale.returned_total = sum((i.returned_subtotal for i in items), Decimal("0"))
        sale.returned_profit = sum((i.returned_profit for i in items), Decimal("0"))
        sale.returned_cogs_cash = sum((i.returned_cogs_cash for i in items), Decimal("0"))
        sale.returned_cogs_debt = sum((i.returned_cogs_debt for i in items), Decimal("0"))
        sale.save(
            update_fields=[
                "returned_total",
                "returned_profit",
                "returned_cogs_cash",
                "returned_cogs_debt",
            ]
        )


def noop(apps, schema_editor):
    """Orqaga qaytarishda ma'lumotni buzmaymiz."""


class Migration(migrations.Migration):
    dependencies = [
        ("sales", "0002_sale_total_cogs_cash_sale_total_cogs_debt_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="sale",
            name="returned_total",
            field=models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14),
        ),
        migrations.AddField(
            model_name="sale",
            name="returned_profit",
            field=models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14),
        ),
        migrations.AddField(
            model_name="sale",
            name="returned_cogs_cash",
            field=models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14),
        ),
        migrations.AddField(
            model_name="sale",
            name="returned_cogs_debt",
            field=models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14),
        ),
        migrations.AddField(
            model_name="saleitem",
            name="returned_subtotal",
            field=models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14),
        ),
        migrations.AddField(
            model_name="saleitem",
            name="returned_cogs_cash",
            field=models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14),
        ),
        migrations.AddField(
            model_name="saleitem",
            name="returned_cogs_debt",
            field=models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14),
        ),
        migrations.AddField(
            model_name="saleitem",
            name="returned_profit",
            field=models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14),
        ),
        migrations.AddField(
            model_name="payment",
            name="is_refund",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AlterField(
            model_name="payment",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.RunPython(backfill_returns, noop),
        migrations.AddConstraint(
            model_name="saleitem",
            constraint=models.CheckConstraint(
                condition=models.Q(returned_quantity__lte=models.F("quantity")),
                name="chk_saleitem_returned_lte_quantity",
            ),
        ),
    ]
