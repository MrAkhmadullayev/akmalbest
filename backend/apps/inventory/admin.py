from django.contrib import admin
from .models import Inventory, InventoryTransaction

@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ['product', 'quantity', 'updated_at']
    search_fields = ['product__name', 'product__barcode']

@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ['product', 'transaction_type', 'quantity', 'previous_quantity', 'new_quantity', 'created_at']
    list_filter = ['transaction_type']
    search_fields = ['product__name']
