"""
Ombor hisobini tiklash buyrug'i.

Uch manbani bir xil holatga keltiradi:
  1. Yo'q Inventory qatorlarini yaratadi.
  2. Manfiy qoldiqni 0 ga keltiradi (audit izi bilan).
  3. ``Product.current_stock`` keshini ``Inventory.quantity`` ga tenglashtiradi.
  4. Partiyalar yig'indisini qoldiqqa moslaydi.

Standart holatda FAQAT ko'rsatadi. Yozish uchun --apply kerak.

    python manage.py stock_reconcile              # dry-run
    python manage.py stock_reconcile --apply
    python manage.py stock_reconcile --apply --source=ledger

``--source`` qoldiqni qaysi manbadan olishni belgilaydi:
    inventory (standart) — Inventory.quantity ga ishonadi
    ledger               — InventoryTransaction tarixidan qayta hisoblaydi
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum

from apps.inventory.models import Inventory, InventoryBatch, InventoryTransaction, TransactionType
from apps.products.models import Product

from .stock_audit import ledger_balance


class Command(BaseCommand):
    help = "Ombor qoldig'i, kesh va partiyalarni bir xil holatga keltiradi."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="O'zgarishlarni haqiqatan yozish")
        parser.add_argument(
            "--source",
            choices=["inventory", "ledger"],
            default="inventory",
            help="Haqiqiy qoldiq manbasi (standart: inventory)",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]
        source = options["source"]

        if not apply_changes:
            self.stdout.write(self.style.WARNING("DRY-RUN — hech narsa yozilmaydi. Yozish uchun --apply qo'shing.\n"))

        batch_totals = {
            b["product"]: b["total"] or 0
            for b in InventoryBatch.objects.values("product").annotate(total=Sum("current_quantity"))
        }

        created_rows = 0
        fixed_negative = 0
        fixed_cache = 0
        fixed_batches = 0

        for product in Product.objects.all().order_by("name"):
            inventory = Inventory.objects.filter(product=product).first()

            if inventory is None:
                created_rows += 1
                self.stdout.write(f"  [+] Inventory yaratiladi: {product.name} → {max(product.current_stock, 0)}")
                if apply_changes:
                    inventory = Inventory.objects.create(product=product, quantity=max(product.current_stock, 0))
                else:
                    continue

            target = inventory.quantity
            if source == "ledger":
                led_qty, tx_count = ledger_balance(product)
                if tx_count:
                    target = led_qty

            if target < 0:
                fixed_negative += 1
                self.stdout.write(
                    self.style.ERROR(f"  [!] Manfiy qoldiq: {product.name} {target} → 0")
                )
                target = 0

            with transaction.atomic():
                # 1. Qoldiq
                if inventory.quantity != target:
                    self.stdout.write(f"  [~] Qoldiq: {product.name} {inventory.quantity} → {target}")
                    if apply_changes:
                        previous = inventory.quantity
                        inventory.quantity = target
                        inventory.save(update_fields=["quantity", "updated_at"])
                        InventoryTransaction.objects.create(
                            product=product,
                            transaction_type=(
                                TransactionType.ADJUSTMENT_IN
                                if target > previous
                                else TransactionType.ADJUSTMENT_OUT
                            ),
                            quantity=abs(target - previous),
                            previous_quantity=previous,
                            new_quantity=target,
                            reference_type="RECONCILE",
                            notes=f"Avtomatik tiklash ({source}): {previous} → {target}",
                        )

                # 2. Kesh
                if product.current_stock != target:
                    fixed_cache += 1
                    self.stdout.write(f"  [~] Kesh: {product.name} {product.current_stock} → {target}")
                    if apply_changes:
                        Product.objects.filter(pk=product.pk).update(current_stock=target)

                # 3. Partiyalar
                batch_qty = batch_totals.get(product.id, 0)
                if batch_qty != target:
                    fixed_batches += 1
                    self.stdout.write(f"  [~] Partiya: {product.name} {batch_qty} → {target}")
                    if apply_changes:
                        from apps.inventory.services import InventoryService

                        InventoryService.sync_batches_to_quantity(product)

        self.stdout.write("")
        self.stdout.write(f"Yaratilgan Inventory qatorlari : {created_rows}")
        self.stdout.write(f"Tuzatilgan manfiy qoldiqlar   : {fixed_negative}")
        self.stdout.write(f"Tuzatilgan kesh qiymatlari     : {fixed_cache}")
        self.stdout.write(f"Tuzatilgan partiya qoldiqlari  : {fixed_batches}")

        if apply_changes:
            self.stdout.write(self.style.SUCCESS("\nTiklash yakunlandi."))
        else:
            self.stdout.write(self.style.WARNING("\nDRY-RUN edi — hech narsa o'zgarmadi."))
