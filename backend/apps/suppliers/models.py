"""
Supplier, Purchase, and PurchaseItem models.
"""
import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal


class PaymentMethod(models.TextChoices):
    CASH = 'CASH', 'Naqd'
    DEBT = 'DEBT', 'Nasiya'


class Supplier(models.Model):
    """Supplier of alcoholic beverages."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True)
    contact_person = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'suppliers'
        ordering = ['name']
        verbose_name = 'Yetkazib beruvchi'
        verbose_name_plural = 'Yetkazib beruvchilar'

    def __str__(self):
        return self.name


class Purchase(models.Model):
    """Purchase order from supplier."""

    class StatusChoices(models.TextChoices):
        PENDING = 'PENDING', 'Kutilmoqda'
        COMPLETED = 'COMPLETED', 'Bajarildi'
        CANCELLED = 'CANCELLED', 'Bekor qilindi'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT,
        related_name='purchases', db_index=True
    )
    invoice_number = models.CharField(max_length=100, blank=True)
    total = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))]
    )
    status = models.CharField(
        max_length=20, choices=StatusChoices.choices,
        default=StatusChoices.COMPLETED
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='purchases'
    )
    purchase_date = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'purchases'
        ordering = ['-purchase_date']
        verbose_name = 'Xarid'
        verbose_name_plural = 'Xaridlar'

    def __str__(self):
        return f"Xarid #{self.id} - {self.supplier.name}"


class PurchaseItem(models.Model):
    """Individual items within a purchase order."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purchase = models.ForeignKey(
        Purchase, on_delete=models.CASCADE, related_name='items'
    )
    product = models.ForeignKey(
        'products.Product', on_delete=models.PROTECT, related_name='purchase_items'
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    purchase_price = models.DecimalField(
        max_digits=14, decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))]
    )
    payment_method = models.CharField(
        max_length=10, choices=PaymentMethod.choices,
        default=PaymentMethod.CASH
    )
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))

    class Meta:
        db_table = 'purchase_items'
        verbose_name = 'Xarid elementi'
        verbose_name_plural = 'Xarid elementlari'

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"

    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.purchase_price
        super().save(*args, **kwargs)


class SupplierDebt(models.Model):
    """Debt owed to a supplier for credit purchases."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT,
        related_name='debts', db_index=True
    )
    purchase = models.OneToOneField(
        Purchase, on_delete=models.PROTECT,
        related_name='debt', null=True, blank=True
    )
    original_amount = models.DecimalField(
        max_digits=14, decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))]
    )
    paid_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))]
    )
    remaining_amount = models.DecimalField(
        max_digits=14, decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))]
    )
    debt_date = models.DateField(db_index=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('ACTIVE', 'Faol'),
            ('PARTIALLY_PAID', "Qisman to'langan"),
            ('PAID', "To'langan")
        ],
        default='ACTIVE', db_index=True
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'supplier_debts'
        ordering = ['-created_at']
        verbose_name = 'Yetkazib beruvchi qarzi'
        verbose_name_plural = 'Yetkazib beruvchi qarzlari'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(remaining_amount__gte=0),
                name='chk_supplier_debt_remaining_non_negative'
            ),
            models.CheckConstraint(
                condition=models.Q(paid_amount__gte=0),
                name='chk_supplier_debt_paid_non_negative'
            ),
        ]

    def __str__(self):
        return f"Qarz: {self.supplier.name} - {self.remaining_amount} UZS"


class SupplierDebtPayment(models.Model):
    """Payment made to a supplier to settle debt."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    debt = models.ForeignKey(SupplierDebt, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(
        max_digits=14, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    payment_method = models.CharField(
        max_length=10,
        choices=[('CASH', 'Naqd'), ('TRANSFER', 'Pul o\'tkazma')],
        default='CASH'
    )
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='supplier_debt_payments_made'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'supplier_debt_payments'
        ordering = ['-created_at']
        verbose_name = 'Yetkazib beruvchi qarzi to\'lovi'
        verbose_name_plural = 'Yetkazib beruvchi qarzi to\'lovlari'

    def __str__(self):
        return f"{self.amount} UZS - {self.debt.supplier.name}"
