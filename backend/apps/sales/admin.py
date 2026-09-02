from django.contrib import admin

from .models import Payment, Sale, SaleItem


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['sale_number', 'cashier', 'customer', 'total', 'payment_method', 'status', 'created_at']
    list_filter = ['payment_method', 'status']
    search_fields = ['sale_number', 'customer__full_name']

@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ['sale', 'product_name_snapshot', 'quantity', 'selling_price_snapshot', 'subtotal']

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['sale', 'amount', 'payment_method', 'created_at']
