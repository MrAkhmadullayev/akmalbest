"""
Sale, SaleItem, and Payment models.
"""
import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal


class PaymentMethod(models.TextChoices):
    CASH = 'CASH', 'Naqd'
    CARD = 'CARD', 'Karta'
    DEBT = 'DEBT', 'Nasiya'


class SaleStatus(models.TextChoices):
    COMPLETED = 'COMPLETED', 'Bajarildi'
    CANCELLED = 'CANCELLED', 'Bekor qilindi'
    RETURNED = 'RETURNED', 'Qaytarildi'
    PARTIALLY_RETURNED = 'PARTIALLY_RETURNED', 'Qisman qaytarildi'


class Sale(models.Model):
    """A completed sale transaction."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sale_number = models.CharField(max_length=20, unique=True, db_index=True)
    cashier = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='sales'
    )
    customer = models.ForeignKey(
        'customers.Customer', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='sales'
    )
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    discount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    profit = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    total_cogs_cash = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    total_cogs_debt = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    payment_method = models.CharField(max_length=10, choices=PaymentMethod.choices)
    status = models.CharField(
        max_length=20, choices=SaleStatus.choices,
        default=SaleStatus.COMPLETED, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sales'
        ordering = ['-created_at']
        verbose_name = 'Savdo'
        verbose_name_plural = 'Savdolar'

    def __str__(self):
        return f"Savdo #{self.sale_number}"


class SaleItem(models.Model):
    """Individual item within a sale with price snapshots."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(
        'products.Product', on_delete=models.PROTECT, related_name='sale_items'
    )
    # Price snapshots - historical accuracy
    product_name_snapshot = models.CharField(max_length=255)
    barcode_snapshot = models.CharField(max_length=50)
    purchase_price_snapshot = models.DecimalField(max_digits=14, decimal_places=2)
    selling_price_snapshot = models.DecimalField(max_digits=14, decimal_places=2)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    returned_quantity = models.PositiveIntegerField(default=0)
    discount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    cogs_cash = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    cogs_debt = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    profit = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))

    class Meta:
        db_table = 'sale_items'
        verbose_name = 'Savdo elementi'
        verbose_name_plural = 'Savdo elementlari'

    def __str__(self):
        return f"{self.product_name_snapshot} x{self.quantity}"


class Payment(models.Model):
    """Payment record for a sale."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(
        max_digits=14, decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))]
    )
    payment_method = models.CharField(max_length=10, choices=PaymentMethod.choices)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='payments'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']
        verbose_name = "To'lov"
        verbose_name_plural = "To'lovlar"

    def __str__(self):
        return f"{self.amount} UZS - {self.payment_method}"
