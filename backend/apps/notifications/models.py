"""Notification model."""

import uuid

from django.conf import settings
from django.db import models


class NotificationType(models.TextChoices):
    LOW_STOCK = "LOW_STOCK", "Kam qoldiq"
    OUT_OF_STOCK = "OUT_OF_STOCK", "Tugagan"
    DEBT_DUE = "DEBT_DUE", "Qarz muddati"
    DEBT_OVERDUE = "DEBT_OVERDUE", "Qarz muddati o'tgan"
    DEBT_UPCOMING = "DEBT_UPCOMING", "Qarz muddati yaqinlashmoqda"
    SYSTEM = "SYSTEM", "Tizim"


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
        help_text="Null = all users",
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    type = models.CharField(max_length=20, choices=NotificationType.choices, db_index=True)
    # Takrorlanishni to'sish kaliti, masalan "LOW_STOCK:<product_id>".
    # O'qilmagan bir xil kalitli bildirishnoma bo'lsa, yangisi yaratilmaydi —
    # aks holda har savdoda yangi qator qo'shilib, jadval cheksiz o'sardi.
    reference_key = models.CharField(max_length=100, blank=True, db_index=True)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
        verbose_name = "Bildirishnoma"
        verbose_name_plural = "Bildirishnomalar"

    def __str__(self):
        return self.title
