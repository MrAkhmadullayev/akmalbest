"""Reports app models."""

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models


class ShiftReport(models.Model):
    """A record of a completed shift (Z-Report)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shift_number = models.CharField(max_length=20, unique=True, db_index=True)
    opened_at = models.DateTimeField(db_index=True)
    closed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="closed_shifts"
    )

    # Aggregated Stats
    total_sales = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    total_cash = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    total_card = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    total_debt = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))

    total_profit = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    total_expenses = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))

    sales_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "shift_reports"
        ordering = ["-closed_at"]
        verbose_name = "Smena Hisoboti"
        verbose_name_plural = "Smena Hisobotlari"

    def __str__(self):
        return f"Smena #{self.shift_number} ({self.closed_at.strftime('%Y-%m-%d %H:%M')})"
