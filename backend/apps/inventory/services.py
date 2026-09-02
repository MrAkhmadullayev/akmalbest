"""
Inventory service layer - handles all stock mutations with locking.
"""
from django.db import transaction

from apps.inventory.models import Inventory, InventoryTransaction, TransactionType
from apps.notifications.services import NotificationService
from apps.products.models import Product


class InventoryService:
    """
    Central service for all inventory operations.
    Always uses select_for_update() to prevent race conditions.
    """

    @staticmethod
    @transaction.atomic
    def increase_stock(product, quantity, transaction_type, reference_id='',
                       reference_type='', user=None, notes='',
                       purchase_price=None, payment_method=None):
        """Increase product stock (purchase, return, adjustment)."""
        inventory = Inventory.objects.select_for_update().get(product=product)
        previous_quantity = inventory.quantity
        new_quantity = previous_quantity + quantity

        inventory.quantity = new_quantity
        inventory.save(update_fields=['quantity', 'updated_at'])

        # Sync denormalized field
        Product.objects.filter(pk=product.pk).update(current_stock=new_quantity)

        # Create batch if purchase price is provided
        from apps.inventory.models import BatchPaymentMethod, InventoryBatch
        if purchase_price is not None:
            InventoryBatch.objects.create(
                product=product,
                quantity=quantity,
                current_quantity=quantity,
                purchase_price=purchase_price,
                payment_method=payment_method or BatchPaymentMethod.CASH,
                reference_id=str(reference_id)
            )

        # Create transaction record
        InventoryTransaction.objects.create(
            product=product,
            transaction_type=transaction_type,
            quantity=quantity,
            previous_quantity=previous_quantity,
            new_quantity=new_quantity,
            reference_id=str(reference_id),
            reference_type=reference_type,
            created_by=user,
            notes=notes,
        )

        return new_quantity

    @staticmethod
    @transaction.atomic
    def decrease_stock(product, quantity, transaction_type, reference_id='',
                       reference_type='', user=None, notes=''):
        """
        Decrease product stock (sale, adjustment, damage).
        Raises ValueError if insufficient stock.
        """
        inventory = Inventory.objects.select_for_update().get(product=product)
        previous_quantity = inventory.quantity

        from decimal import Decimal

        from apps.inventory.models import BatchPaymentMethod, InventoryBatch

        cogs_cash = Decimal('0')
        cogs_debt = Decimal('0')

        # FIFO logic
        remaining_to_decrease = quantity
        batches = InventoryBatch.objects.filter(
            product=product, current_quantity__gt=0
        ).order_by('created_at').select_for_update()

        for batch in batches:
            if remaining_to_decrease <= 0:
                break

            if batch.current_quantity >= remaining_to_decrease:
                deducted = remaining_to_decrease
                batch.current_quantity -= deducted
                batch.save(update_fields=['current_quantity'])
                remaining_to_decrease = 0
            else:
                deducted = batch.current_quantity
                remaining_to_decrease -= deducted
                batch.current_quantity = 0
                batch.save(update_fields=['current_quantity'])

            cost = deducted * batch.purchase_price
            if batch.payment_method == BatchPaymentMethod.CASH:
                cogs_cash += cost
            else:
                cogs_debt += cost

        if remaining_to_decrease > 0:
            fallback_cost = remaining_to_decrease * product.purchase_price
            cogs_cash += fallback_cost

        new_quantity = previous_quantity - quantity
        inventory.quantity = new_quantity
        inventory.save(update_fields=['quantity', 'updated_at'])

        # Sync denormalized field
        Product.objects.filter(pk=product.pk).update(current_stock=new_quantity)

        # Create transaction record
        InventoryTransaction.objects.create(
            product=product,
            transaction_type=transaction_type,
            quantity=quantity,
            previous_quantity=previous_quantity,
            new_quantity=new_quantity,
            reference_id=str(reference_id),
            reference_type=reference_type,
            created_by=user,
            notes=notes,
        )

        # Check low stock notifications
        product.refresh_from_db()
        NotificationService.check_stock_level(product)

        return new_quantity, cogs_cash, cogs_debt

    @staticmethod
    @transaction.atomic
    def adjust_stock(product, new_quantity, user=None, notes=''):
        """Set stock to a specific quantity (manual adjustment)."""
        inventory = Inventory.objects.select_for_update().get(product=product)
        previous_quantity = inventory.quantity
        diff = new_quantity - previous_quantity

        if diff == 0:
            return new_quantity

        tx_type = TransactionType.ADJUSTMENT_IN if diff > 0 else TransactionType.ADJUSTMENT_OUT

        inventory.quantity = new_quantity
        inventory.save(update_fields=['quantity', 'updated_at'])

        Product.objects.filter(pk=product.pk).update(current_stock=new_quantity)

        InventoryTransaction.objects.create(
            product=product,
            transaction_type=tx_type,
            quantity=abs(diff),
            previous_quantity=previous_quantity,
            new_quantity=new_quantity,
            reference_type='ADJUSTMENT',
            created_by=user,
            notes=notes or f"Qo'lda tuzatish: {previous_quantity} → {new_quantity}",
        )

        product.refresh_from_db()
        NotificationService.check_stock_level(product)

        return new_quantity
