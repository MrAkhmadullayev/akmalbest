"""
Sale service layer - handles complete sale lifecycle with atomic transactions.
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from apps.inventory.services import InventoryService
from apps.inventory.models import TransactionType
from apps.products.models import Product
from apps.audit.services import AuditService
from .models import Sale, SaleItem, Payment, PaymentMethod, SaleStatus


class SaleService:
    """
    Central sale processing engine.
    All operations use transaction.atomic() with select_for_update().
    """

    @staticmethod
    def generate_sale_number():
        """Generate unique sale number: YYYYMMDD-XXXX."""
        today = timezone.now()
        prefix = today.strftime('%Y%m%d')
        last_sale = Sale.objects.filter(
            sale_number__startswith=prefix
        ).order_by('-sale_number').first()

        if last_sale:
            last_num = int(last_sale.sale_number.split('-')[1])
            new_num = last_num + 1
        else:
            new_num = 1

        return f"{prefix}-{new_num:04d}"

    @staticmethod
    @transaction.atomic
    def create_sale(items_data, payment_method, cashier, customer=None,
                    discount=Decimal('0'), paid_amount=None, due_date=None):
        """
        Create a complete sale with atomic guarantees.

        items_data: list of dicts with keys:
            - product_id (UUID)
            - quantity (int)
            - discount (Decimal, optional)

        Returns: (sale, change_amount)
        """
        # 1. Validate and lock products
        sale_items = []
        subtotal = Decimal('0')

        for item_data in items_data:
            product = Product.objects.select_for_update().get(
                pk=item_data['product_id'], is_active=True
            )
            qty = int(item_data['quantity'])
            item_discount = Decimal(str(item_data.get('discount', '0')))

            # Stock validation
            if product.current_stock < qty:
                raise ValueError(
                    f"Omborda yetarli mahsulot mavjud emas. "
                    f"'{product.name}' - Mavjud: {product.current_stock}, So'ralgan: {qty}"
                )

            item_subtotal = (product.selling_price * qty) - item_discount

            sale_items.append({
                'product': product,
                'quantity': qty,
                'discount': item_discount,
                'subtotal': item_subtotal,
            })

            subtotal += item_subtotal

        # 2. Calculate totals (backend authoritative)
        grand_total = subtotal - discount
        if grand_total < 0:
            grand_total = Decimal('0')

        # 3. Create sale
        sale = Sale.objects.create(
            sale_number=SaleService.generate_sale_number(),
            cashier=cashier,
            customer=customer,
            subtotal=subtotal,
            discount=discount,
            total=grand_total,
            profit=Decimal('0'),
            total_cogs_cash=Decimal('0'),
            total_cogs_debt=Decimal('0'),
            payment_method=payment_method,
            status=SaleStatus.COMPLETED,
        )

        # 4. Create sale items with snapshots & decrease inventory
        total_profit = Decimal('0')
        total_cogs_cash = Decimal('0')
        total_cogs_debt = Decimal('0')

        for item in sale_items:
            product = item['product']

            # Decrease inventory with locking
            new_qty, cogs_cash, cogs_debt = InventoryService.decrease_stock(
                product=product,
                quantity=item['quantity'],
                transaction_type=TransactionType.SALE,
                reference_id=str(sale.id),
                reference_type='SALE',
                user=cashier,
                notes=f"Savdo: {sale.sale_number}",
            )

            item_profit = item['subtotal'] - (cogs_cash + cogs_debt)
            total_profit += item_profit
            total_cogs_cash += cogs_cash
            total_cogs_debt += cogs_debt

            SaleItem.objects.create(
                sale=sale,
                product=product,
                product_name_snapshot=product.name,
                barcode_snapshot=product.barcode,
                purchase_price_snapshot=product.purchase_price,
                selling_price_snapshot=product.selling_price,
                quantity=item['quantity'],
                discount=item['discount'],
                subtotal=item['subtotal'],
                profit=item_profit,
                cogs_cash=cogs_cash,
                cogs_debt=cogs_debt,
            )

        sale.profit = total_profit
        sale.total_cogs_cash = total_cogs_cash
        sale.total_cogs_debt = total_cogs_debt
        sale.save(update_fields=['profit', 'total_cogs_cash', 'total_cogs_debt'])

        # 5. Create payment record
        change_amount = Decimal('0')
        if payment_method == PaymentMethod.CASH:
            actual_paid = Decimal(str(paid_amount)) if paid_amount else grand_total
            change_amount = actual_paid - grand_total
            if change_amount < 0:
                raise ValueError("To'lov miqdori yetarli emas.")

        if payment_method != PaymentMethod.DEBT:
            Payment.objects.create(
                sale=sale,
                amount=grand_total,
                payment_method=payment_method,
                created_by=cashier,
            )

        # 6. Create debt if payment method is DEBT
        if payment_method == PaymentMethod.DEBT:
            if not customer:
                raise ValueError("Nasiya savdo uchun mijoz tanlanishi shart.")
            if not due_date:
                raise ValueError("Nasiya savdo uchun muddat kiritilishi shart.")

            from apps.debts.models import Debt
            Debt.objects.create(
                customer=customer,
                sale=sale,
                original_amount=grand_total,
                paid_amount=Decimal('0'),
                remaining_amount=grand_total,
                debt_date=timezone.now().date(),
                due_date=due_date,
                status='ACTIVE',
            )

        # 7. Audit log
        AuditService.log(
            user=cashier,
            action='CREATE',
            model_name='Sale',
            object_id=str(sale.id),
            new_data={
                'sale_number': sale.sale_number,
                'total': str(sale.total),
                'payment_method': sale.payment_method,
                'items_count': len(sale_items),
            },
        )

        return sale, change_amount

    @staticmethod
    @transaction.atomic
    def return_sale_item(sale_item, return_quantity, user):
        """
        Process a return for a sale item.
        Validates return quantity and restores inventory.
        """
        available_to_return = sale_item.quantity - sale_item.returned_quantity

        if return_quantity > available_to_return:
            raise ValueError(
                f"Qaytarish miqdori sotilgan miqdordan oshib ketdi. "
                f"Qaytarish mumkin: {available_to_return}"
            )

        # Increase inventory
        InventoryService.increase_stock(
            product=sale_item.product,
            quantity=return_quantity,
            transaction_type=TransactionType.RETURN,
            reference_id=str(sale_item.sale.id),
            reference_type='SALE_RETURN',
            user=user,
            notes=f"Qaytarish: {sale_item.sale.sale_number} - {sale_item.product_name_snapshot}",
        )

        # Update sale item
        sale_item.returned_quantity += return_quantity
        sale_item.save(update_fields=['returned_quantity'])

        # Update sale status
        sale = sale_item.sale
        all_items = sale.items.all()
        all_fully_returned = all(i.returned_quantity >= i.quantity for i in all_items)
        any_returned = any(i.returned_quantity > 0 for i in all_items)

        if all_fully_returned:
            sale.status = SaleStatus.RETURNED
        elif any_returned:
            sale.status = SaleStatus.PARTIALLY_RETURNED
        sale.save(update_fields=['status', 'updated_at'])

        # Audit log
        AuditService.log(
            user=user,
            action='RETURN',
            model_name='SaleItem',
            object_id=str(sale_item.id),
            new_data={
                'sale_number': sale.sale_number,
                'product': sale_item.product_name_snapshot,
                'return_quantity': return_quantity,
            },
        )

        return sale_item
