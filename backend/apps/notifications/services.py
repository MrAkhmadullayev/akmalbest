"""Notification service - creates system notifications."""
from .models import Notification, NotificationType


class NotificationService:
    """Creates notifications for stock levels and debt reminders."""

    @staticmethod
    def check_stock_level(product):
        """Generate stock notifications based on product thresholds."""
        if product.current_stock <= 0:
            Notification.objects.create(
                title="🔴 Mahsulot tugadi",
                message=f"{product.name} mahsuloti tugadi.",
                type=NotificationType.OUT_OF_STOCK,
            )
        elif product.current_stock <= product.min_stock:
            Notification.objects.create(
                title="⚠ Mahsulot kam qoldi",
                message=f"{product.name} mahsuloti kam qoldi. Qoldiq: {product.current_stock} dona.",
                type=NotificationType.LOW_STOCK,
            )

    @staticmethod
    def create_debt_notification(debt, notification_type):
        """Create a debt-related notification."""
        type_messages = {
            NotificationType.DEBT_UPCOMING: (
                "🟡 Qarzni to'lash muddatiga yaqinlashmoqda",
                f"{debt.customer.full_name} - {debt.remaining_amount} UZS. Muddat: {debt.due_date}"
            ),
            NotificationType.DEBT_DUE: (
                "🔔 Bugun to'lash kerak",
                f"{debt.customer.full_name} - {debt.remaining_amount} UZS. Bugun to'lash muddati."
            ),
            NotificationType.DEBT_OVERDUE: (
                "🔴 Qarz muddati o'tgan",
                f"{debt.customer.full_name} - {debt.remaining_amount} UZS. Qarz muddati o'tgan!"
            ),
        }

        title, message = type_messages.get(
            notification_type,
            ("Qarz haqida xabar", f"{debt.customer.full_name} - {debt.remaining_amount} UZS")
        )

        Notification.objects.create(
            title=title,
            message=message,
            type=notification_type,
        )
