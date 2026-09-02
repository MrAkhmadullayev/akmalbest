from django.contrib import admin

from .models import Debt, DebtPayment


@admin.register(Debt)
class DebtAdmin(admin.ModelAdmin):
    list_display = ['customer', 'original_amount', 'remaining_amount', 'due_date', 'status']
    list_filter = ['status']
    search_fields = ['customer__full_name']

@admin.register(DebtPayment)
class DebtPaymentAdmin(admin.ModelAdmin):
    list_display = ['debt', 'amount', 'payment_method', 'created_at']
