"""``Product.current_stock`` uchun manfiy bo'lmaslik cheklovi.

Ma'lumot ``inventory.0005_stock_integrity`` da tuzatilgani uchun shu
migratsiyaga bog'lanadi.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0002_initial"),
        ("inventory", "0005_stock_integrity"),
    ]

    operations = [
        migrations.AlterField(
            model_name="product",
            name="current_stock",
            field=models.IntegerField(default=0, help_text="Joriy zaxira (Inventory.quantity keshi)"),
        ),
        migrations.AddConstraint(
            model_name="product",
            constraint=models.CheckConstraint(
                condition=models.Q(current_stock__gte=0), name="chk_product_stock_non_negative"
            ),
        ),
    ]
