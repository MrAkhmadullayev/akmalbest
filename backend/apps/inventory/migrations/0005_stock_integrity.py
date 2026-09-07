"""
Ombor hisobining yaxlitligini tiklaydi va DB darajasida himoyani qaytaradi.

Tartib muhim: avval mavjud ma'lumot tuzatiladi, KEYIN cheklov qo'yiladi —
aks holda buzilgan qatorlar tufayli migratsiya yiqilardi.

0004 migratsiyasida ``chk_inventory_quantity_non_negative`` cheklovi olib
tashlangan edi; aynan shu manfiy qoldiqlarga yo'l ochib bergan.
"""

from django.db import migrations, models


def repair_stock(apps, schema_editor):
    Product = apps.get_model("products", "Product")
    Inventory = apps.get_model("inventory", "Inventory")
    InventoryBatch = apps.get_model("inventory", "InventoryBatch")
    InventoryTransaction = apps.get_model("inventory", "InventoryTransaction")

    db = schema_editor.connection.alias

    existing = {i.product_id: i for i in Inventory.objects.using(db).all()}

    for product in Product.objects.using(db).all().iterator():
        inventory = existing.get(product.id)

        # 1. Yo'q Inventory qatorini yaratamiz.
        if inventory is None:
            inventory = Inventory.objects.using(db).create(
                product=product, quantity=max(product.current_stock, 0)
            )

        target = inventory.quantity

        # 2. Manfiy qoldiqni nolga keltiramiz va izini qoldiramiz.
        if target < 0:
            InventoryTransaction.objects.using(db).create(
                product=product,
                transaction_type="ADJUSTMENT_IN",
                quantity=abs(target),
                previous_quantity=target,
                new_quantity=0,
                reference_type="MIGRATION_REPAIR",
                notes=f"Migratsiya tiklashi: manfiy qoldiq {target} → 0",
            )
            target = 0
            inventory.quantity = 0
            inventory.save(update_fields=["quantity"])

        # 3. Keshni qoldiqqa tenglashtiramiz.
        if product.current_stock != target:
            Product.objects.using(db).filter(pk=product.pk).update(current_stock=target)

        # 4. Partiyalar yig'indisini qoldiqqa moslaymiz.
        batch_total = 0
        for batch in InventoryBatch.objects.using(db).filter(product=product):
            batch_total += batch.current_quantity

        diff = target - batch_total
        if diff > 0:
            InventoryBatch.objects.using(db).create(
                product=product,
                quantity=diff,
                current_quantity=diff,
                purchase_price=product.purchase_price,
                payment_method="CASH",
                reference_id="MIGRATION_REPAIR",
            )
        elif diff < 0:
            remaining = -diff
            batches = InventoryBatch.objects.using(db).filter(
                product=product, current_quantity__gt=0
            ).order_by("created_at")
            for batch in batches:
                if remaining <= 0:
                    break
                deducted = min(batch.current_quantity, remaining)
                batch.current_quantity -= deducted
                batch.save(update_fields=["current_quantity"])
                remaining -= deducted


def noop(apps, schema_editor):
    """Orqaga qaytarishda ma'lumotni buzmaymiz."""


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0004_remove_inventory_chk_inventory_quantity_non_negative"),
        ("products", "0002_initial"),
    ]

    operations = [
        migrations.RunPython(repair_stock, noop),
        migrations.AddConstraint(
            model_name="inventory",
            constraint=models.CheckConstraint(
                condition=models.Q(quantity__gte=0), name="chk_inventory_quantity_non_negative"
            ),
        ),
    ]
