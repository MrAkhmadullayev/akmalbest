"""Celery tasks for scheduled background jobs."""
from datetime import timedelta

from celery import shared_task
from django.db import models
from django.utils import timezone


@shared_task
def check_debt_due_dates():
    """Check for upcoming, due today, and overdue debts. Runs daily via Celery Beat."""
    from apps.debts.models import Debt, DebtStatus
    from apps.notifications.models import NotificationType
    from apps.notifications.services import NotificationService

    today = timezone.now().date()
    upcoming_date = today + timedelta(days=3)

    # Mark overdue debts
    overdue_debts = Debt.objects.filter(
        due_date__lt=today,
        status__in=[DebtStatus.ACTIVE, DebtStatus.PARTIALLY_PAID]
    )
    for debt in overdue_debts:
        debt.status = DebtStatus.OVERDUE
        debt.save(update_fields=['status', 'updated_at'])
        NotificationService.create_debt_notification(debt, NotificationType.DEBT_OVERDUE)

    # Due today
    due_today = Debt.objects.filter(
        due_date=today,
        status__in=[DebtStatus.ACTIVE, DebtStatus.PARTIALLY_PAID]
    )
    for debt in due_today:
        NotificationService.create_debt_notification(debt, NotificationType.DEBT_DUE)

    # Upcoming (within 3 days)
    upcoming = Debt.objects.filter(
        due_date__range=(today + timedelta(days=1), upcoming_date),
        status__in=[DebtStatus.ACTIVE, DebtStatus.PARTIALLY_PAID]
    )
    for debt in upcoming:
        NotificationService.create_debt_notification(debt, NotificationType.DEBT_UPCOMING)


@shared_task
def check_low_stock():
    """Check for low stock products. Runs daily via Celery Beat."""
    from apps.notifications.services import NotificationService
    from apps.products.models import Product

    low_stock_products = Product.objects.filter(
        is_active=True,
        current_stock__lte=models.F('warning_stock'),
        current_stock__gt=0,
    )
    for product in low_stock_products:
        NotificationService.check_stock_level(product)

    out_of_stock = Product.objects.filter(
        is_active=True,
        current_stock__lte=0,
    )
    for product in out_of_stock:
        NotificationService.check_stock_level(product)
