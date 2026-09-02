"""Debt and DebtPayment models."""
import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class DebtStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Faol'
    PARTIALLY_PAID = 'PARTIALLY_PAID', 'Qisman to\'langan'
    PAID = 'PAID', 'To\'langan'
    OVERDUE = 'OVERDUE', 'Muddati o\'tgan'


class Debt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        'customers.Customer', on_delete=models.PROTECT,
        related_name='debts', db_index=True
    )
    sale = models.OneToOneField(
        'sales.Sale', on_delete=models.PROTECT,
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
    due_date = models.DateField(db_index=True)
    status = models.CharField(
        max_length=20, choices=DebtStatus.choices,
        default=DebtStatus.ACTIVE, db_index=True
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'debts'
        ordering = ['-created_at']
        verbose_name = 'Qarz'
        verbose_name_plural = 'Qarzlar'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(remaining_amount__gte=0),
                name='chk_debt_remaining_non_negative'
            ),
            models.CheckConstraint(
                condition=models.Q(paid_amount__gte=0),
                name='chk_debt_paid_non_negative'
            ),
        ]

    def __str__(self):
        return f"Qarz: {self.customer.full_name} - {self.remaining_amount} UZS"


class DebtPayment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    debt = models.ForeignKey(Debt, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(
        max_digits=14, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    payment_method = models.CharField(
        max_length=10,
        choices=[('CASH', 'Naqd'), ('CARD', 'Karta')],
        default='CASH'
    )
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='debt_payments_received'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'debt_payments'
        ordering = ['-created_at']
        verbose_name = 'Qarz to\'lovi'
        verbose_name_plural = 'Qarz to\'lovlari'

    def __str__(self):
        return f"{self.amount} UZS - {self.debt.customer.full_name}"
