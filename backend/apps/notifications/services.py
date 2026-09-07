"""Notification service - creates system notifications."""

from .models import Notification, NotificationType


class NotificationService:
    """Creates notifications for stock levels and debt reminders."""

    @staticmethod
    def _emit(title, message, notification_type, reference_key):
        """Create a notification unless an identical unread one already exists.

        Ilgari har bir savdoda yangi qator yaratilardi va kam qoldiqli mahsulot
        bir necha marta sotilsa, bildirishnomalar jadvali cheksiz o'sardi.
        """
        if reference_key and Notification.objects.filter(
            reference_key=reference_key, is_read=False
        ).exists():
            return None

        return Notification.objects.create(
            title=title,
            message=message,
            type=notification_type,
            reference_key=reference_key,
        )

    @staticmethod
    def check_stock_level(product):
        """Generate stock notifications based on product thresholds.

        Qoldiq yetarli bo'lib qolsa, eski ogohlantirishlar o'qilgan deb
        belgilanadi — panelda "tugagan" deb turgan mahsulot omborga kirim
        qilingandan keyin ham osilib qolmasin.
        """
        stock_keys = [f"LOW_STOCK:{product.id}", f"OUT_OF_STOCK:{product.id}"]

        if product.current_stock <= 0:
            Notification.objects.filter(reference_key=f"LOW_STOCK:{product.id}", is_read=False).update(is_read=True)
            NotificationService._emit(
                title="🔴 Mahsulot tugadi",
                message=f"{product.name} mahsuloti tugadi.",
                notification_type=NotificationType.OUT_OF_STOCK,
                reference_key=f"OUT_OF_STOCK:{product.id}",
            )
        elif product.current_stock <= product.min_stock:
            Notification.objects.filter(
                reference_key=f"OUT_OF_STOCK:{product.id}", is_read=False
            ).update(is_read=True)
            NotificationService._emit(
                title="⚠ Mahsulot kam qoldi",
                message=f"{product.name} mahsuloti kam qoldi. Qoldiq: {product.current_stock} dona.",
                notification_type=NotificationType.LOW_STOCK,
                reference_key=f"LOW_STOCK:{product.id}",
            )
        else:
            # Qoldiq tiklandi — ochiq ogohlantirishlarni yopamiz.
            Notification.objects.filter(reference_key__in=stock_keys, is_read=False).update(is_read=True)

    @staticmethod
    def create_debt_notification(debt, notification_type):
        """Create a debt-related notification."""
        type_messages = {
            NotificationType.DEBT_UPCOMING: (
                "🟡 Qarzni to'lash muddatiga yaqinlashmoqda",
                f"{debt.customer.full_name} - {debt.remaining_amount} UZS. Muddat: {debt.due_date}",
            ),
            NotificationType.DEBT_DUE: (
                "🔔 Bugun to'lash kerak",
                f"{debt.customer.full_name} - {debt.remaining_amount} UZS. Bugun to'lash muddati.",
            ),
            NotificationType.DEBT_OVERDUE: (
                "🔴 Qarz muddati o'tgan",
                f"{debt.customer.full_name} - {debt.remaining_amount} UZS. Qarz muddati o'tgan!",
            ),
        }

        title, message = type_messages.get(
            notification_type, ("Qarz haqida xabar", f"{debt.customer.full_name} - {debt.remaining_amount} UZS")
        )

        return NotificationService._emit(
            title=title,
            message=message,
            notification_type=notification_type,
            reference_key=f"{notification_type}:{debt.id}",
        )
