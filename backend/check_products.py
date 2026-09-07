import django, os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from apps.products.models import Product
from apps.inventory.models import Inventory

for p in Product.objects.all():
    inv = Inventory.objects.filter(product=p).first()
    inv_qty = inv.quantity if inv else "NO INV"
    print(f"{p.name} | barcode={p.barcode} | active={p.is_active} | current_stock={p.current_stock} | inv_qty={inv_qty}")
