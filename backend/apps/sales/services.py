"""
Sale service layer - handles complete sale lifecycle with atomic transactions.
"""

from collections import OrderedDict
from decimal import ROUND_HALF_UP, Decimal

from django.db import IntegrityError, transaction
from django.db.models import Max
from django.utils import timezone

from apps.audit.services import AuditService
from apps.inventory.exceptions import InsufficientStockError
from apps.inventory.models import TransactionType
from apps.inventory.services import InventoryService
from apps.products.models import Product

from .models import Payment, PaymentMethod, Sale, SaleItem, SaleStatus

TWOPLACES = Decimal("0.01")


def _money(value):
    """Round a Decimal to 2 decimal places the way money should be rounded."""
    return Decimal(value).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


class SaleService:
    """
    Central sale processing engine.
    All operations use transaction.atomic() with select_for_update().
    """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def generate_sale_number():
        """Generate unique sale number: YYYYMMDD-XXXX.

        Bir vaqtning o'zida ikki kassir sotganda bir xil raqam chiqib
        IntegrityError bo'lardi. Endi raqam MAX() dan olinadi va yozish
        chaqiruvchi tomonda qayta urinish bilan o'ralgan.
        """
        prefix = timezone.now().strftime("%Y%m%d")
        last_number = Sale.objects.filter(sale_number__startswith=prefix).aggregate(m=Max("sale_number"))["m"]

        if last_number:
            try:
                new_num = int(last_number.split("-")[1]) + 1
            except (IndexError, ValueError):
                new_num = Sale.objects.filter(sale_number__startswith=prefix).count() + 1
        else:
            new_num = 1

        return f"{prefix}-{new_num:04d}"

    @staticmethod
    def _merge_items(items_data):
        """Collapse duplicate product lines into one line per product.

        Bir savdoda bir mahsulot ikki qatorda kelsa, har bir qator alohida
        tekshirilib, ikkalasi ham "yetarli" deb topilardi va natijada qoldiq
        manfiyga tushardi. Shuning uchun avval qatorlarni birlashtiramiz.
        """
        merged = OrderedDict()
        for item in items_data:
            product_id = str(item["product_id"])
            qty = int(item["quantity"])
            if qty < 1:
                raise ValueError("Miqdor 1 dan kam bo'lishi mumkin emas.")
            discount = Decimal(str(item.get("discount", "0")))
            if discount < 0:
                raise ValueError("Chegirma manfiy bo'lishi mumkin emas.")

            if product_id in merged:
                merged[product_id]["quantity"] += qty
                merged[product_id]["discount"] += discount
            else:
                merged[product_id] = {"product_id": item["product_id"], "quantity": qty, "discount": discount}

        return list(merged.values())

    @staticmethod
    def _allocate_sale_discount(sale_items, sale_discount, base_amount):
        """Spread the sale-level discount across lines and set each line's subtotal.

        Har bir qatorning ``discount`` maydoniga ulushi qo'shiladi, ``subtotal``
        esa yakuniy (chegirmadan keyingi) qiymat bo'ladi. Yaxlitlash qoldig'i
        oxirgi qatorga yoziladi — shunda qatorlar yig'indisi savdo summasiga
        tiyin-ba-tiyin teng bo'ladi.
        """
        for item in sale_items:
            item["subtotal"] = _money(item["gross"] - item["discount"])

        if sale_discount <= 0 or base_amount <= 0:
            return

        allocated = Decimal("0")
        for item in sale_items[:-1]:
            share = _money(sale_discount * (item["subtotal"] / base_amount))
            share = min(share, item["subtotal"])
            item["discount"] = _money(item["discount"] + share)
            item["subtotal"] = _money(item["subtotal"] - share)
            allocated += share

        last = sale_items[-1]
        remainder = _money(sale_discount - allocated)
        remainder = min(remainder, last["subtotal"])
        last["discount"] = _money(last["discount"] + remainder)
        last["subtotal"] = _money(last["subtotal"] - remainder)

    @staticmethod
    def _recalculate_sale(sale):
        """Recompute the sale's returned totals and status from its items."""
        items = list(sale.items.all())

        sale.returned_total = _money(sum((i.returned_subtotal for i in items), Decimal("0")))
        sale.returned_profit = _money(sum((i.returned_profit for i in items), Decimal("0")))
        sale.returned_cogs_cash = _money(sum((i.returned_cogs_cash for i in items), Decimal("0")))
        sale.returned_cogs_debt = _money(sum((i.returned_cogs_debt for i in items), Decimal("0")))

        if sale.status != SaleStatus.CANCELLED:
            all_returned = items and all(i.returned_quantity >= i.quantity for i in items)
            any_returned = any(i.returned_quantity > 0 for i in items)
            if all_returned:
                sale.status = SaleStatus.RETURNED
            elif any_returned:
                sale.status = SaleStatus.PARTIALLY_RETURNED
            else:
                sale.status = SaleStatus.COMPLETED

        sale.save(
            update_fields=[
                "returned_total",
                "returned_profit",
                "returned_cogs_cash",
                "returned_cogs_debt",
                "status",
                "updated_at",
            ]
        )
        return sale

    # ------------------------------------------------------------------
    # Sale creation
    # ------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def create_sale(
        items_data, payment_method, cashier, customer=None, discount=Decimal("0"), paid_amount=None, due_date=None
    ):
        """
        Create a complete sale with atomic guarantees.

        items_data: list of dicts with keys:
            - product_id (UUID)
            - quantity (int)
            - discount (Decimal, optional)

        Returns: (sale, change_amount)
        """
        discount = Decimal(str(discount or 0))
        if discount < 0:
            raise ValueError("Chegirma manfiy bo'lishi mumkin emas.")

        merged_items = SaleService._merge_items(items_data)

        # Nasiya shartlarini ombordan oldin tekshiramiz — keraksiz qulflash
        # va rollback bo'lmasin.
        if payment_method == PaymentMethod.DEBT:
            if not customer:
                raise ValueError("Nasiya savdo uchun mijoz tanlanishi shart.")
            if not due_date:
                raise ValueError("Nasiya savdo uchun muddat kiritilishi shart.")

        # 1. Mahsulotlarni qulflaymiz (deadlock bo'lmasligi uchun barqaror tartibda)
        sale_items = []
        gross_subtotal = Decimal("0")  # chegirmasiz, sof narx × miqdor
        line_discount_total = Decimal("0")

        for item_data in sorted(merged_items, key=lambda i: str(i["product_id"])):
            try:
                product = Product.objects.select_for_update().get(pk=item_data["product_id"], is_active=True)
            except Product.DoesNotExist:
                raise ValueError("Mahsulot topilmadi yoki faol emas.") from None

            qty = item_data["quantity"]
            item_discount = item_data["discount"]
            line_gross = _money(product.selling_price * qty)

            # Erta tekshiruv: qoldiq AVTORITAR manbadan (Inventory) o'qiladi va
            # yetmasa savdo yozuvi yaratilishidan OLDIN to'xtatiladi.
            # Yakuniy, qulflangan tekshiruv baribir decrease_stock ichida
            # bajariladi — bu shunchaki keraksiz ishni oldini oladi.
            inventory = InventoryService.peek(product)
            if inventory.quantity < qty:
                raise InsufficientStockError(product, qty, inventory.quantity)

            if item_discount > line_gross:
                raise ValueError(f"'{product.name}' uchun chegirma summadan katta bo'lishi mumkin emas.")

            sale_items.append(
                {
                    "product": product,
                    "quantity": qty,
                    "gross": line_gross,
                    "discount": item_discount,
                }
            )
            gross_subtotal += line_gross
            line_discount_total += item_discount

        gross_subtotal = _money(gross_subtotal)
        after_line_discounts = _money(gross_subtotal - line_discount_total)

        # 2. Yakuniy summa (backend avtoritar)
        if discount > after_line_discounts:
            raise ValueError("Chegirma savdo summasidan katta bo'lishi mumkin emas.")

        # Savdo darajasidagi chegirmani qatorlarga proporsional taqsimlaymiz.
        # Aks holda to'liq qaytarishda qatorlar yig'indisi savdo summasiga teng
        # bo'lmay qolardi va foyda ham chegirma miqdoricha oshib ketardi.
        SaleService._allocate_sale_discount(sale_items, discount, after_line_discounts)

        subtotal = gross_subtotal
        total_discount = _money(line_discount_total + discount)
        grand_total = _money(sum((i["subtotal"] for i in sale_items), Decimal("0")))

        # 3. Naqd to'lovni savdo yaratilishidan OLDIN tekshiramiz.
        change_amount = Decimal("0")
        if payment_method == PaymentMethod.CASH:
            actual_paid = _money(paid_amount) if paid_amount is not None else grand_total
            change_amount = _money(actual_paid - grand_total)
            if change_amount < 0:
                raise ValueError("To'lov miqdori yetarli emas.")

        # 4. Savdoni yaratamiz (raqam to'qnashuvida qayta urinamiz)
        sale = SaleService._create_sale_row(
            cashier=cashier,
            customer=customer,
            subtotal=subtotal,
            discount=total_discount,
            grand_total=grand_total,
            payment_method=payment_method,
        )

        # 5. Qatorlar + ombordan chiqim
        total_profit = Decimal("0")
        total_cogs_cash = Decimal("0")
        total_cogs_debt = Decimal("0")

        for item in sale_items:
            product = item["product"]

            # decrease_stock endi yetarlilikni O'ZI tekshiradi (qulflangan
            # Inventory qatori bo'yicha) va yetmasa InsufficientStockError
            # ko'taradi — butun tranzaksiya orqaga qaytadi.
            _new_qty, cogs_cash, cogs_debt = InventoryService.decrease_stock(
                product=product,
                quantity=item["quantity"],
                transaction_type=TransactionType.SALE,
                reference_id=str(sale.id),
                reference_type="SALE",
                user=cashier,
                notes=f"Savdo: {sale.sale_number}",
            )

            cogs_cash = _money(cogs_cash)
            cogs_debt = _money(cogs_debt)
            item_profit = _money(item["subtotal"] - (cogs_cash + cogs_debt))

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
                quantity=item["quantity"],
                discount=item["discount"],
                subtotal=item["subtotal"],
                profit=item_profit,
                cogs_cash=cogs_cash,
                cogs_debt=cogs_debt,
            )

        sale.profit = _money(total_profit)
        sale.total_cogs_cash = _money(total_cogs_cash)
        sale.total_cogs_debt = _money(total_cogs_debt)
        sale.save(update_fields=["profit", "total_cogs_cash", "total_cogs_debt", "updated_at"])

        # 6. To'lov yozuvi
        if payment_method != PaymentMethod.DEBT:
            Payment.objects.create(
                sale=sale,
                amount=grand_total,
                payment_method=payment_method,
                created_by=cashier,
            )

        # 7. Nasiya
        if payment_method == PaymentMethod.DEBT:
            from apps.debts.models import Debt

            Debt.objects.create(
                customer=customer,
                sale=sale,
                original_amount=grand_total,
                paid_amount=Decimal("0"),
                remaining_amount=grand_total,
                debt_date=timezone.now().date(),
                due_date=due_date,
                status="ACTIVE",
            )

        AuditService.log(
            user=cashier,
            action="CREATE",
            model_name="Sale",
            object_id=str(sale.id),
            new_data={
                "sale_number": sale.sale_number,
                "total": str(sale.total),
                "payment_method": sale.payment_method,
                "items_count": len(sale_items),
            },
        )

        return sale, change_amount

    @staticmethod
    def _create_sale_row(cashier, customer, subtotal, discount, grand_total, payment_method, attempts=5):
        """Insert the Sale row, retrying on sale_number collisions."""
        last_error = None
        for _ in range(attempts):
            try:
                with transaction.atomic():
                    return Sale.objects.create(
                        sale_number=SaleService.generate_sale_number(),
                        cashier=cashier,
                        customer=customer,
                        subtotal=subtotal,
                        discount=discount,
                        total=grand_total,
                        profit=Decimal("0"),
                        total_cogs_cash=Decimal("0"),
                        total_cogs_debt=Decimal("0"),
                        payment_method=payment_method,
                        status=SaleStatus.COMPLETED,
                    )
            except IntegrityError as exc:
                last_error = exc
                continue
        raise ValueError("Savdo raqamini yaratib bo'lmadi, qayta urinib ko'ring.") from last_error

    # ------------------------------------------------------------------
    # Returns
    # ------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def return_sale_item(sale_item, return_quantity, user, _skip_recalc=False):
        """
        Process a return for a sale item.
        Validates return quantity, restores inventory and reverses the money.
        """
        return_quantity = int(return_quantity)
        if return_quantity < 1:
            raise ValueError("Qaytarish miqdori 1 dan kam bo'lishi mumkin emas.")

        # Qator qulflanadi — bir vaqtda ikki qaytarish qo'sh hisoblanmasin.
        sale_item = SaleItem.objects.select_for_update().select_related("sale", "product").get(pk=sale_item.pk)

        available_to_return = sale_item.quantity - sale_item.returned_quantity
        if return_quantity > available_to_return:
            raise ValueError(
                f"Qaytarish miqdori sotilgan miqdordan oshib ketdi. Qaytarish mumkin: {available_to_return}"
            )

        # Omborga qaytaramiz — tovar qaysi partiyadan chiqqan bo'lsa, o'shanga.
        InventoryService.increase_stock(
            product=sale_item.product,
            quantity=return_quantity,
            transaction_type=TransactionType.RETURN,
            reference_id=str(sale_item.sale.id),
            reference_type="SALE_RETURN",
            user=user,
            notes=f"Qaytarish: {sale_item.sale.sale_number} - {sale_item.product_name_snapshot}",
            purchase_price=sale_item.purchase_price_snapshot,
            restore_batches=True,
        )

        # Pul tomonini kumulyativ nisbat bo'yicha hisoblaymiz: har safar "shu
        # paytgacha qaytarilishi kerak bo'lgan jami" dan avvalgisini ayiramiz.
        # Shunda bo'lak-bo'lak qaytarishlar yig'indisi to'liq summaga tiyin-ba-tiyin
        # teng chiqadi (proporsional yaxlitlashda qoldiq yig'ilib qolmaydi).
        previous_returned_qty = sale_item.returned_quantity
        new_returned_qty = previous_returned_qty + return_quantity
        fully_returned = new_returned_qty >= sale_item.quantity

        if fully_returned:
            target_subtotal = sale_item.subtotal
            target_cogs_cash = sale_item.cogs_cash
            target_cogs_debt = sale_item.cogs_debt
            target_profit = sale_item.profit
        else:
            ratio = Decimal(new_returned_qty) / Decimal(sale_item.quantity)
            target_subtotal = _money(sale_item.subtotal * ratio)
            target_cogs_cash = _money(sale_item.cogs_cash * ratio)
            target_cogs_debt = _money(sale_item.cogs_debt * ratio)
            target_profit = _money(target_subtotal - (target_cogs_cash + target_cogs_debt))

        refund_subtotal = _money(target_subtotal - sale_item.returned_subtotal)

        sale_item.returned_quantity = new_returned_qty
        sale_item.returned_subtotal = target_subtotal
        sale_item.returned_cogs_cash = target_cogs_cash
        sale_item.returned_cogs_debt = target_cogs_debt
        sale_item.returned_profit = target_profit

        sale_item.save(
            update_fields=[
                "returned_quantity",
                "returned_subtotal",
                "returned_cogs_cash",
                "returned_cogs_debt",
                "returned_profit",
            ]
        )

        sale = sale_item.sale
        SaleService._register_refund(sale=sale, amount=refund_subtotal, user=user)

        if not _skip_recalc:
            SaleService._recalculate_sale(sale)

        AuditService.log(
            user=user,
            action="RETURN",
            model_name="SaleItem",
            object_id=str(sale_item.id),
            new_data={
                "sale_number": sale.sale_number,
                "product": sale_item.product_name_snapshot,
                "return_quantity": return_quantity,
                "refund_amount": str(refund_subtotal),
            },
        )

        return sale_item

    @staticmethod
    def _register_refund(sale, amount, user):
        """Reverse the money for a returned amount.

        Nasiya savdoda avval qarz kamaytiriladi. Agar mijoz o'sha qismni
        allaqachon to'lagan bo'lsa (qarz qoldig'i yetmasa), ortib qolgan summa
        unga naqd qaytariladi. Naqd/kartada esa to'g'ridan-to'g'ri kassadan
        chiqim yoziladi.
        """
        if amount <= 0:
            return

        refund_in_cash = amount
        if sale.payment_method == PaymentMethod.DEBT:
            refund_in_cash = SaleService._reduce_sale_debt(sale, amount, user)

        if refund_in_cash <= 0:
            return

        Payment.objects.create(
            sale=sale,
            amount=refund_in_cash,
            # Nasiya savdo qaytarilganda ortiqcha pul naqd qaytariladi.
            payment_method=(
                PaymentMethod.CASH if sale.payment_method == PaymentMethod.DEBT else sale.payment_method
            ),
            is_refund=True,
            created_by=user,
        )

    @staticmethod
    def _reduce_sale_debt(sale, amount, user):
        """Reduce the debt tied to ``sale`` by ``amount``.

        Qarz qoplay olmagan qism (mijoz allaqachon to'lab bo'lgan qism)
        qaytariladi — uni chaqiruvchi naqd qaytarim sifatida yozadi.
        """
        from apps.debts.models import Debt, DebtStatus

        debt = Debt.objects.select_for_update().filter(sale=sale).first()
        if not debt:
            # Qarz yozuvi yo'q — hammasi naqd qaytariladi.
            return amount

        reduction = min(amount, debt.remaining_amount)
        leftover = _money(amount - reduction)

        debt.remaining_amount = _money(debt.remaining_amount - reduction)
        debt.original_amount = _money(max(debt.original_amount - amount, Decimal("0")))

        # Mijoz qaytarilgan tovar uchun ortiqcha to'lab qo'ygan bo'lsa, o'sha
        # ortiqcha pul naqd qaytariladi va qarz yozuvi muvozanatga keltiriladi.
        if leftover > 0:
            debt.paid_amount = _money(max(debt.paid_amount - leftover, Decimal("0")))

        if debt.original_amount < debt.paid_amount:
            debt.original_amount = debt.paid_amount

        if debt.remaining_amount <= 0:
            debt.remaining_amount = Decimal("0")
            debt.status = DebtStatus.PAID
        elif debt.paid_amount > 0:
            debt.status = DebtStatus.PARTIALLY_PAID

        debt.save(
            update_fields=["original_amount", "paid_amount", "remaining_amount", "status", "updated_at"]
        )

        AuditService.log(
            user=user,
            action="UPDATE",
            model_name="Debt",
            object_id=str(debt.id),
            new_data={
                "reason": "SALE_RETURN",
                "sale_number": sale.sale_number,
                "reduced_by": str(reduction),
                "cash_refund": str(leftover),
                "remaining": str(debt.remaining_amount),
            },
        )

        return leftover

    # ------------------------------------------------------------------
    # Cancellation
    # ------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def cancel_sale(sale, user):
        """Cancel an entire sale: restore stock, reverse money, close the debt.

        Butun amal bitta tranzaksiyada — yarim bajarilgan holat qolmaydi.
        """
        sale = Sale.objects.select_for_update().get(pk=sale.pk)

        if sale.status == SaleStatus.CANCELLED:
            raise ValueError("Bu savdo allaqachon bekor qilingan.")
        if sale.status not in (SaleStatus.COMPLETED, SaleStatus.PARTIALLY_RETURNED):
            raise ValueError("Faqat bajarilgan savdolarni bekor qilish mumkin.")

        for item in sale.items.select_related("product").all():
            remaining = item.quantity - item.returned_quantity
            if remaining > 0:
                SaleService.return_sale_item(item, remaining, user, _skip_recalc=True)

        sale.status = SaleStatus.CANCELLED
        sale.save(update_fields=["status", "updated_at"])
        SaleService._recalculate_sale(sale)

        # Nasiya savdo bekor qilinsa qarz ham yopilishi shart.
        SaleService._close_sale_debt(sale, user)

        AuditService.log(
            user=user,
            action="CANCEL",
            model_name="Sale",
            object_id=str(sale.id),
            new_data={"sale_number": sale.sale_number, "total": str(sale.total)},
        )

        return sale

    @staticmethod
    def _close_sale_debt(sale, user):
        """Zero out the debt of a cancelled sale."""
        from apps.debts.models import Debt, DebtStatus

        debt = Debt.objects.select_for_update().filter(sale=sale).first()
        if not debt or debt.remaining_amount <= 0:
            return

        debt.remaining_amount = Decimal("0")
        debt.original_amount = debt.paid_amount
        debt.status = DebtStatus.PAID
        debt.notes = (debt.notes + "\n" if debt.notes else "") + f"Savdo bekor qilindi ({sale.sale_number})."
        debt.save(update_fields=["remaining_amount", "original_amount", "status", "notes", "updated_at"])

        AuditService.log(
            user=user,
            action="CANCEL",
            model_name="Debt",
            object_id=str(debt.id),
            new_data={"reason": "SALE_CANCELLED", "sale_number": sale.sale_number},
        )
