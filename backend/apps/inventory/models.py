"""
Inventory and InventoryTransaction models.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Inventory(models.Model):
    """One-to-one inventory record per product."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.OneToOneField("products.Product", on_delete=models.CASCADE, related_name="inventory")
    quantity = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "inventory"
        verbose_name = "Ombor"
        verbose_name_plural = "Ombor"

    def __str__(self):
        return f"{self.product.name}: {self.quantity}"


class BatchPaymentMethod(models.TextChoices):
    CASH = "CASH", "Naqd"
    DEBT = "DEBT", "Nasiya"


class InventoryBatch(models.Model):
    """FIFO tracking of inventory batches."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="batches", db_index=True)
    quantity = models.IntegerField(validators=[MinValueValidator(0)])
    current_quantity = models.IntegerField(validators=[MinValueValidator(0)])
    purchase_price = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    payment_method = models.CharField(
        max_length=10, choices=BatchPaymentMethod.choices, default=BatchPaymentMethod.CASH, db_index=True
    )
    reference_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "inventory_batches"
        ordering = ["created_at"]  # FIFO order
        verbose_name = "Ombor partiyasi"
        verbose_name_plural = "Ombor partiyalari"
        constraints = [
            models.CheckConstraint(condition=models.Q(current_quantity__gte=0), name="chk_batch_quantity_non_negative"),
        ]

    def __str__(self):
        return f"{self.product.name} ({self.current_quantity}/{self.quantity}) - {self.payment_method}"


class TransactionType(models.TextChoices):
    PURCHASE = "PURCHASE", "Sotib olish"
    SALE = "SALE", "Sotish"
    RETURN = "RETURN", "Qaytarish"
    ADJUSTMENT_IN = "ADJUSTMENT_IN", "Tuzatish (Kirish)"
    ADJUSTMENT_OUT = "ADJUSTMENT_OUT", "Tuzatish (Chiqish)"
    DAMAGE = "DAMAGE", "Buzilgan"
    OTHER = "OTHER", "Boshqa"


class InventoryTransaction(models.Model):
    """Tracks every inventory change with full audit trail."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        "products.Product", on_delete=models.CASCADE, related_name="inventory_transactions", db_index=True
    )
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices, db_index=True)
    quantity = models.IntegerField(help_text="Miqdor o'zgarishi")
    previous_quantity = models.IntegerField()
    new_quantity = models.IntegerField()
    reference_id = models.CharField(max_length=255, blank=True, help_text="Bog'liq hujjat ID")
    reference_type = models.CharField(max_length=50, blank=True, help_text="Bog'liq hujjat turi")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="inventory_transactions"
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "inventory_transactions"
        ordering = ["-created_at"]
        verbose_name = "Ombor harakati"
        verbose_name_plural = "Ombor harakatlari"

    def __str__(self):
        return f"{self.product.name} | {self.transaction_type} | {self.quantity}"
