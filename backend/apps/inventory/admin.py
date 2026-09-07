from django.contrib import admin

from .models import Inventory, InventoryBatch, InventoryTransaction


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ["product", "quantity", "stock_status", "updated_at"]
    search_fields = ["product__name", "product__barcode"]
    # Qoldiqni qo'lda o'zgartirish partiya (tannarx) qatlamini buzadi va
    # keshni og'diradi. Tuzatish faqat "Ombor → Tuzatish" orqali —
    # u InventoryService orqali uch manbani birga yangilaydi.
    readonly_fields = ["product", "quantity", "updated_at"]

    def has_add_permission(self, request):
        return False


@admin.register(InventoryBatch)
class InventoryBatchAdmin(admin.ModelAdmin):
    list_display = ["product", "quantity", "current_quantity", "purchase_price", "payment_method", "created_at"]
    list_filter = ["payment_method"]
    search_fields = ["product__name", "product__barcode"]
    readonly_fields = [f.name for f in InventoryBatch._meta.fields]

    def has_add_permission(self, request):
        return False


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ["product", "transaction_type", "quantity", "previous_quantity", "new_quantity", "created_at"]
    list_filter = ["transaction_type"]
    search_fields = ["product__name"]
    # Audit izi — o'zgartirilmaydi.
    readonly_fields = [f.name for f in InventoryTransaction._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
