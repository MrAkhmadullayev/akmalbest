"""Smena hisobotiga kassani solishtirish uchun maydonlar.

Ilgari Z-hisobotda faqat savdo naqdi bor edi; nasiya to'lovlari va
qaytarimlar hisobga olinmagani uchun kassa hech qachon to'g'ri kelmasdi.
"""

from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="shiftreport",
            name="total_returns",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0"),
                help_text="Smenada qaytarilgan summa",
                max_digits=14,
            ),
        ),
        migrations.AddField(
            model_name="shiftreport",
            name="total_debt_payments_cash",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0"),
                help_text="Nasiya bo'yicha naqd tushum",
                max_digits=14,
            ),
        ),
        migrations.AddField(
            model_name="shiftreport",
            name="total_debt_payments_card",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0"),
                help_text="Nasiya bo'yicha karta tushumi",
                max_digits=14,
            ),
        ),
        migrations.AddField(
            model_name="shiftreport",
            name="expected_cash",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0"),
                help_text="Smena oxirida kassada bo'lishi kerak bo'lgan naqd",
                max_digits=14,
            ),
        ),
    ]
