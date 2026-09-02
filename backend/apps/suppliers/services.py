"""
Purchase service layer.
"""
from decimal import Decimal
from django.db import transaction
from apps.inventory.services import InventoryService
from apps.inventory.models import TransactionType
from .models import Purchase, PurchaseItem, SupplierDebt, PaymentMethod


class PurchaseService:
    """Handles purchase creation with inventory updates."""

    @staticmethod
    @transaction.atomic
    def create_purchase(supplier, items_data, user, invoice_number='',
                        purchase_date=None, notes=''):
        """
        Create a purchase and increase inventory for each item.
        items_data: list of dicts with 'product', 'quantity', 'purchase_price'
        """
        from django.utils import timezone

        purchase = Purchase.objects.create(
            supplier=supplier,
            invoice_number=invoice_number,
            purchase_date=purchase_date or timezone.now().date(),
            created_by=user,
            notes=notes,
            status=Purchase.StatusChoices.COMPLETED,
        )

        total = Decimal('0')
        debt_amount = Decimal('0')

        for item_data in items_data:
            product = item_data['product']
            quantity = item_data['quantity']
            price = Decimal(str(item_data['purchase_price']))
            payment_method = item_data.get('payment_method', PaymentMethod.CASH)

            purchase_item = PurchaseItem.objects.create(
                purchase=purchase,
                product=product,
                quantity=quantity,
                purchase_price=price,
                payment_method=payment_method
            )
            total += purchase_item.subtotal

            if payment_method == PaymentMethod.DEBT:
                debt_amount += purchase_item.subtotal

            # Increase inventory
            InventoryService.increase_stock(
                product=product,
                quantity=quantity,
                transaction_type=TransactionType.PURCHASE,
                reference_id=str(purchase.id),
                reference_type='PURCHASE',
                user=user,
                notes=f"Xarid: {invoice_number or purchase.id}",
                purchase_price=price,
                payment_method=payment_method
            )

            # Update product purchase price if changed
            if product.purchase_price != price:
                product.purchase_price = price
                product.save(update_fields=['purchase_price', 'updated_at'])

        purchase.total = total
        purchase.save(update_fields=['total'])

        if debt_amount > 0:
            SupplierDebt.objects.create(
                supplier=supplier,
                purchase=purchase,
                original_amount=debt_amount,
                remaining_amount=debt_amount,
                debt_date=purchase.purchase_date
            )

        return purchase
