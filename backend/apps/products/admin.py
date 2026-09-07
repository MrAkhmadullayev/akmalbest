from django.contrib import admin

from .models import Brand, Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active", "created_at"]
    search_fields = ["name"]


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active", "created_at"]
    search_fields = ["name"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "barcode", "category", "brand", "selling_price", "current_stock", "is_active"]
    list_filter = ["category", "brand", "is_active"]
    search_fields = ["name", "barcode"]
    ordering = ["name"]
    # current_stock — Inventory.quantity keshi. Admin panel orqali qo'lda
    # o'zgartirilsa ombor hisobi buziladi, shuning uchun faqat o'qish uchun.
    # Qoldiqni o'zgartirish: Ombor → Tuzatish yoki mahsulotga kirim qo'shish.
    readonly_fields = ["current_stock"]
