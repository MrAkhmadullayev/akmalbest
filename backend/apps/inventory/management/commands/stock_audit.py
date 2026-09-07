"""
Ombor hisobini tekshirish buyrug'i.

Uch manbani solishtiradi va farqlarni ko'rsatadi. HECH NARSANI O'ZGARTIRMAYDI.

    python manage.py stock_audit
    python manage.py stock_audit --only-broken
    python manage.py stock_audit --csv > audit.csv
"""

import csv
import sys

from django.core.management.base import BaseCommand
from django.db.models import Sum

from apps.inventory.models import Inventory, InventoryBatch, InventoryTransaction
from apps.products.models import Product


def ledger_balance(product):
    """Qoldiqni InventoryTransaction tarixidan qayta hisoblaydi."""
    balance = 0
    txs = InventoryTransaction.objects.filter(product=product).order_by("created_at")
    for tx in txs:
        if tx.transaction_type in ("PURCHASE", "RETURN", "ADJUSTMENT_IN"):
            balance += tx.quantity
        elif tx.transaction_type in ("SALE", "ADJUSTMENT_OUT", "DAMAGE"):
            balance -= tx.quantity
        else:
            # OTHER — new_quantity ga ishonamiz
            balance = tx.new_quantity
    return balance, txs.count()


def collect_rows():
    rows = []
    inventories = {i.product_id: i.quantity for i in Inventory.objects.all()}
    batch_totals = {
        b["product"]: b["total"] or 0
        for b in InventoryBatch.objects.values("product").annotate(total=Sum("current_quantity"))
    }

    for product in Product.objects.all().order_by("name"):
        inv_qty = inventories.get(product.id)
        batch_qty = batch_totals.get(product.id, 0)
        led_qty, tx_count = ledger_balance(product)

        problems = []
        if inv_qty is None:
            problems.append("INVENTORY_YO'Q")
            inv_qty = 0
        if product.current_stock != inv_qty:
            problems.append("KESH_OG'GAN")
        if batch_qty != inv_qty:
            problems.append("PARTIYA_OG'GAN")
        if tx_count and led_qty != inv_qty:
            problems.append("TARIX_MOS_EMAS")
        if inv_qty < 0 or product.current_stock < 0:
            problems.append("MANFIY")

        rows.append(
            {
                "id": str(product.id),
                "name": product.name,
                "barcode": product.barcode,
                "current_stock": product.current_stock,
                "inventory_qty": inv_qty,
                "batch_qty": batch_qty,
                "ledger_qty": led_qty,
                "tx_count": tx_count,
                "problems": ",".join(problems),
            }
        )
    return rows


class Command(BaseCommand):
    help = "Ombor hisobining uch manbasini solishtiradi (o'zgartirmaydi)."

    def add_arguments(self, parser):
        parser.add_argument("--only-broken", action="store_true", help="Faqat muammoli mahsulotlarni ko'rsatish")
        parser.add_argument("--csv", action="store_true", help="CSV formatida chiqarish")

    def handle(self, *args, **options):
        rows = collect_rows()
        broken = [r for r in rows if r["problems"]]
        shown = broken if options["only_broken"] else rows

        if options["csv"]:
            writer = csv.DictWriter(sys.stdout, fieldnames=list(rows[0].keys()) if rows else [])
            writer.writeheader()
            writer.writerows(shown)
            return

        self.stdout.write("")
        self.stdout.write(
            f"{'Mahsulot':<38}{'kesh':>7}{'ombor':>8}{'partiya':>9}{'tarix':>7}  muammo"
        )
        self.stdout.write("-" * 100)

        for r in shown:
            name = (r["name"][:35] + "...") if len(r["name"]) > 38 else r["name"]
            line = (
                f"{name:<38}{r['current_stock']:>7}{r['inventory_qty']:>8}"
                f"{r['batch_qty']:>9}{r['ledger_qty']:>7}  {r['problems']}"
            )
            if r["problems"]:
                self.stdout.write(self.style.WARNING(line))
            else:
                self.stdout.write(line)

        self.stdout.write("")
        self.stdout.write(f"Jami mahsulot: {len(rows)}")
        if broken:
            self.stdout.write(self.style.ERROR(f"Muammoli: {len(broken)}"))
            self.stdout.write("")
            self.stdout.write("Tuzatish uchun:  python manage.py stock_reconcile --dry-run")
        else:
            self.stdout.write(self.style.SUCCESS("Barcha manbalar mos — muammo topilmadi."))
