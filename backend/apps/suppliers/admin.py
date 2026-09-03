from django.contrib import admin

from .models import Purchase, PurchaseItem, Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ["name", "contact_person", "phone", "is_active"]
    search_fields = ["name", "phone"]


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ["supplier", "invoice_number", "total", "status", "purchase_date"]
    list_filter = ["status"]


@admin.register(PurchaseItem)
class PurchaseItemAdmin(admin.ModelAdmin):
    list_display = ["purchase", "product", "quantity", "purchase_price", "subtotal"]
