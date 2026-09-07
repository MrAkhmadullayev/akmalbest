"""Inventory signals.

Har bir mahsulotda Inventory qatori bo'lishi kafolatlanadi. Bu ikki narsa
uchun zarur:
  * ``InventoryService`` qulflash uchun qator topa olishi kerak,
  * hisobotlar endi Inventory bo'yicha sanaydi — qatorsiz mahsulot
    "tugagan" ro'yxatiga umuman tushmay qolardi.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.products.models import Product

from .models import Inventory


@receiver(post_save, sender=Product, dispatch_uid="inventory_ensure_row_for_product")
def ensure_inventory_row(sender, instance, created, **kwargs):
    if created:
        Inventory.objects.get_or_create(product=instance, defaults={"quantity": instance.current_stock or 0})
