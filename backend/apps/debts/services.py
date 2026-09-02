"""Debt service layer."""
from decimal import Decimal
from django.db import transaction
from .models import Debt, DebtPayment, DebtStatus
from apps.audit.services import AuditService


class DebtService:
    """Handles debt payment processing."""

    @staticmethod
    @transaction.atomic
    def make_payment(debt, amount, payment_method, received_by, notes=''):
        """
        Process a debt payment.
        Validates payment amount doesn't exceed remaining.
        """
        debt = Debt.objects.select_for_update().get(pk=debt.pk)

        if debt.status == DebtStatus.PAID:
            raise ValueError("Bu qarz allaqachon to'langan.")

        amount = Decimal(str(amount))

        if amount > debt.remaining_amount:
            raise ValueError(
                f"To'lov miqdori qarz qoldig'idan oshib ketdi. "
                f"Qoldiq: {debt.remaining_amount} UZS"
            )

        # Create payment record
        payment = DebtPayment.objects.create(
            debt=debt,
            amount=amount,
            payment_method=payment_method,
            received_by=received_by,
            notes=notes,
        )

        # Update debt
        debt.paid_amount += amount
        debt.remaining_amount -= amount

        if debt.remaining_amount <= 0:
            debt.remaining_amount = Decimal('0')
            debt.status = DebtStatus.PAID
        elif debt.paid_amount > 0:
            debt.status = DebtStatus.PARTIALLY_PAID

        debt.save(update_fields=['paid_amount', 'remaining_amount', 'status', 'updated_at'])

        # Audit
        AuditService.log(
            user=received_by,
            action='PAYMENT',
            model_name='Debt',
            object_id=str(debt.id),
            new_data={
                'payment_amount': str(amount),
                'remaining': str(debt.remaining_amount),
                'status': debt.status,
            },
        )

        return payment
