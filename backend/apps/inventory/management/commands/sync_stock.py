"""
Management command to sync product.current_stock with Inventory.quantity.

Run this once to fix any out-of-sync records caused by previous bugs:
    python manage.py sync_stock

Then verify with:
    python manage.py sync_stock --dry-run
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.inventory.models import Inventory
from apps.products.models import Product


class Command(BaseCommand):
    help = "Sync product.current_stock with the authoritative Inventory.quantity value"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show mismatches without fixing them",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write("=== DRY RUN (no changes will be made) ===\n")

        products = Product.objects.all()
        fixed_count = 0
        mismatch_count = 0
        no_inventory_count = 0

        for product in products:
            try:
                inv = Inventory.objects.get(product=product)
                if product.current_stock != inv.quantity:
                    mismatch_count += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"MISMATCH: [{product.barcode}] {product.name} "
                            f"| product.current_stock={product.current_stock} "
                            f"| inventory.quantity={inv.quantity}"
                        )
                    )
                    if not dry_run:
                        Product.objects.filter(pk=product.pk).update(current_stock=inv.quantity)
                        fixed_count += 1

            except Inventory.DoesNotExist:
                no_inventory_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"NO INVENTORY: [{product.barcode}] {product.name} "
                        f"| product.current_stock={product.current_stock}"
                    )
                )
                if not dry_run:
                    # Create missing inventory record, trusting product.current_stock as initial
                    Inventory.objects.create(product=product, quantity=product.current_stock)
                    self.stdout.write(f"  -> Created Inventory with quantity={product.current_stock}")

        total = products.count()
        ok_count = total - mismatch_count - no_inventory_count

        self.stdout.write("\n=== SUMMARY ===")
        self.stdout.write(f"Total products checked:    {total}")
        self.stdout.write(self.style.SUCCESS(f"OK (in sync):              {ok_count}"))
        self.stdout.write(self.style.WARNING(f"Mismatches found:          {mismatch_count}"))
        self.stdout.write(self.style.ERROR(f"No Inventory record:       {no_inventory_count}"))

        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"\nFixed: {fixed_count + no_inventory_count} records updated/created.")
            )
        else:
            self.stdout.write("\nRe-run without --dry-run to apply fixes.")
