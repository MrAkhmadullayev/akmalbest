"""
Product, Category, and Brand models.
"""
import uuid
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class Category(models.Model):
    """Product category (Vodka, Whisky, Beer, Wine, etc.)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'categories'
        ordering = ['name']
        verbose_name = 'Kategoriya'
        verbose_name_plural = 'Kategoriyalar'

    def __str__(self):
        return self.name


class Brand(models.Model):
    """Product brand."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'brands'
        ordering = ['name']
        verbose_name = 'Brend'
        verbose_name_plural = 'Brendlar'

    def __str__(self):
        return self.name


class Product(models.Model):
    """Product model with barcode, pricing and stock thresholds."""

    class UnitChoices(models.TextChoices):
        BOTTLE = 'bottle', 'Shisha'
        LITER = 'L', 'Litr'
        MILLILITER = 'ml', 'Millilitr'
        PIECE = 'pcs', 'Dona'
        BOX = 'box', 'Quti'
        PACK = 'pack', 'Pachka'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True)
    barcode = models.CharField(max_length=50, unique=True, db_index=True)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT,
        related_name='products', db_index=True
    )
    brand = models.ForeignKey(
        Brand, on_delete=models.PROTECT,
        related_name='products', null=True, blank=True, db_index=True
    )
    volume = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Hajmi (masalan: 0.5, 0.7, 1.0)"
    )
    unit = models.CharField(
        max_length=10, choices=UnitChoices.choices,
        default=UnitChoices.BOTTLE
    )
    purchase_price = models.DecimalField(
        max_digits=14, decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Sotib olish narxi (UZS)"
    )
    selling_price = models.DecimalField(
        max_digits=14, decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Sotish narxi (UZS)"
    )
    min_stock = models.PositiveIntegerField(default=5, help_text="Minimal zaxira")
    warning_stock = models.PositiveIntegerField(default=10, help_text="Ogohlantirish darajasi")
    max_stock = models.PositiveIntegerField(default=100, help_text="Maksimal zaxira")
    current_stock = models.IntegerField(default=0, help_text="Joriy zaxira (denormalized)")
    supplier = models.ForeignKey(
        'suppliers.Supplier', on_delete=models.SET_NULL,
        related_name='products', null=True, blank=True
    )
    expiration_date = models.DateField(null=True, blank=True)
    image = models.FileField(upload_to='products/', null=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'products'
        ordering = ['name']
        verbose_name = 'Mahsulot'
        verbose_name_plural = 'Mahsulotlar'
        indexes = [
            models.Index(fields=['barcode'], name='idx_product_barcode'),
            models.Index(fields=['name'], name='idx_product_name'),
            models.Index(fields=['category'], name='idx_product_category'),
            models.Index(fields=['brand'], name='idx_product_brand'),
            models.Index(fields=['is_active', 'current_stock'], name='idx_product_active_stock'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(purchase_price__gte=0),
                name='chk_product_purchase_price_positive'
            ),
            models.CheckConstraint(
                condition=models.Q(selling_price__gte=0),
                name='chk_product_selling_price_positive'
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.barcode})"

    @property
    def stock_status(self):
        """Return stock status based on thresholds."""
        if self.current_stock <= 0:
            return 'OUT_OF_STOCK'
        elif self.current_stock <= self.min_stock:
            return 'LOW'
        elif self.current_stock <= self.warning_stock:
            return 'WARNING'
        return 'SUFFICIENT'

    @property
    def profit_margin(self):
        """Calculate profit margin per unit."""
        return self.selling_price - self.purchase_price
