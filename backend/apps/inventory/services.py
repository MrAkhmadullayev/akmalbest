"""
Inventory service layer - handles all stock mutations with locking.

Yagona haqiqat manbasi (single source of truth): ``Inventory.quantity``.
``Product.current_stock`` — bir xil tranzaksiya ichida yangilanadigan kesh,
u faqat shu servis orqali yoziladi. ``InventoryBatch`` esa FIFO tannarx
qatlami bo'lib, uning yig'indisi har doim ``Inventory.quantity`` ga teng
bo'lishi kafolatlanadi: har qanday kirim partiya yaratadi, har qanday chiqim
partiyadan yechadi.
"""

from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from apps.inventory.exceptions import InsufficientStockError, InventoryError
from apps.inventory.models import (
    BatchPaymentMethod,
    Inventory,
    InventoryBatch,
    InventoryTransaction,
    TransactionType,
)
from apps.notifications.services import NotificationService
from apps.products.models import Product


class InventoryService:
    """
    Central service for all inventory operations.
    Always uses select_for_update() to prevent race conditions.
    """

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _lock_inventory(product):
        """Return the locked Inventory row for ``product``, creating it if missing.

        Eski ma'lumot yoki admin panel orqali yaratilgan mahsulotlarda Inventory
        yozuvi bo'lmasligi mumkin edi va bu 500 xatoga olib kelardi.
        """
        Inventory.objects.get_or_create(product=product, defaults={"quantity": 0})
        return Inventory.objects.select_for_update().get(product=product)

    @staticmethod
    def _write_quantity(inventory, product, new_quantity):
        """Persist ``new_quantity`` to both the ledger and the denormalized cache."""
        inventory.quantity = new_quantity
        inventory.save(update_fields=["quantity", "updated_at"])
        # Kesh har doim shu yerda, shu tranzaksiya ichida yangilanadi.
        Product.objects.filter(pk=product.pk).update(current_stock=new_quantity)

    @staticmethod
    def _consume_batches(product, quantity):
        """Consume ``quantity`` units FIFO and return ``(cogs_cash, cogs_debt)``.

        Partiyalar yetmay qolgan taqdirda (eski, partiyasiz ma'lumot) qolgan
        qismi mahsulotning joriy tannarxi bo'yicha naqd COGS'ga yoziladi.
        """
        cogs_cash = Decimal("0")
        cogs_debt = Decimal("0")
        remaining = quantity

        batches = (
            InventoryBatch.objects.select_for_update()
            .filter(product=product, current_quantity__gt=0)
            .order_by("created_at")
        )

        for batch in batches:
            if remaining <= 0:
                break

            deducted = min(batch.current_quantity, remaining)
            batch.current_quantity -= deducted
            batch.save(update_fields=["current_quantity"])
            remaining -= deducted

            cost = deducted * batch.purchase_price
            if batch.payment_method == BatchPaymentMethod.CASH:
                cogs_cash += cost
            else:
                cogs_debt += cost

        if remaining > 0:
            cogs_cash += remaining * product.purchase_price

        return cogs_cash, cogs_debt

    @staticmethod
    def _release_batches(product, quantity):
        """Put ``quantity`` units back into recently consumed batches (LIFO).

        Qaytarish/bekor qilishda tovar qaysi partiyadan yechilgan bo'lsa, imkon
        qadar o'sha partiyaga qaytariladi — shunda ombor qiymati va naqd/nasiya
        taqsimoti buzilmaydi. Joy yetmasa, qolgan miqdor qaytariladi va chaqiruvchi
        uni yangi partiya sifatida qo'shadi.
        """
        remaining = quantity

        batches = InventoryBatch.objects.select_for_update().filter(product=product).order_by("-created_at")

        for batch in batches:
            if remaining <= 0:
                break
            free_space = batch.quantity - batch.current_quantity
            if free_space <= 0:
                continue
            restored = min(free_space, remaining)
            batch.current_quantity += restored
            batch.save(update_fields=["current_quantity"])
            remaining -= restored

        return remaining

    @staticmethod
    def peek(product):
        """Return the Inventory row for ``product`` WITHOUT locking it.

        Erta (qulflanmagan) tekshiruvlar uchun. Yakuniy qaror har doim
        ``decrease_stock`` ichida, qulflangan qator bo'yicha qabul qilinadi.
        """
        inventory, _ = Inventory.objects.get_or_create(product=product, defaults={"quantity": 0})
        # Eskirgan keshni jimgina to'g'rilaymiz (eski ma'lumot uchun himoya).
        if product.current_stock != inventory.quantity:
            Product.objects.filter(pk=product.pk).update(current_stock=inventory.quantity)
            product.current_stock = inventory.quantity
        return inventory

    @staticmethod
    def batch_total(product):
        """Sum of remaining units across all batches for ``product``."""
        return (
            InventoryBatch.objects.filter(product=product).aggregate(total=Sum("current_quantity"))["total"] or 0
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def increase_stock(
        product,
        quantity,
        transaction_type,
        reference_id="",
        reference_type="",
        user=None,
        notes="",
        purchase_price=None,
        payment_method=None,
        restore_batches=False,
    ):
        """Increase product stock (purchase, return, adjustment).

        Har qanday kirim partiya qatlamiga ham yoziladi: ``restore_batches=True``
        bo'lsa avval oldin yechilgan partiyalarga qaytariladi (qaytarish/bekor
        qilish uchun), aks holda yangi partiya ochiladi.
        """
        quantity = int(quantity)
        if quantity <= 0:
            raise InventoryError("Miqdor noldan katta bo'lishi kerak.")

        inventory = InventoryService._lock_inventory(product)
        previous_quantity = inventory.quantity
        new_quantity = previous_quantity + quantity

        InventoryService._write_quantity(inventory, product, new_quantity)

        leftover = quantity
        if restore_batches:
            leftover = InventoryService._release_batches(product, quantity)

        # Qolgan (yoki barcha) miqdor uchun yangi partiya ochamiz — shunda
        # partiyalar yig'indisi har doim ombor qoldig'iga teng bo'ladi.
        if leftover > 0:
            effective_price = purchase_price if purchase_price is not None else product.purchase_price
            InventoryBatch.objects.create(
                product=product,
                quantity=leftover,
                current_quantity=leftover,
                purchase_price=effective_price,
                payment_method=payment_method or BatchPaymentMethod.CASH,
                reference_id=str(reference_id),
            )

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
    def decrease_stock(product, quantity, transaction_type, reference_id="", reference_type="", user=None, notes=""):
        """
        Decrease product stock (sale, adjustment, damage).
        Raises InsufficientStockError if stock is insufficient.
        """
        quantity = int(quantity)
        if quantity <= 0:
            raise InventoryError("Miqdor noldan katta bo'lishi kerak.")

        inventory = InventoryService._lock_inventory(product)
        previous_quantity = inventory.quantity

        # Yagona, avtoritar tekshiruv — qulflangan ombor yozuvi bo'yicha.
        if previous_quantity < quantity:
            raise InsufficientStockError(product, quantity, previous_quantity)

        cogs_cash, cogs_debt = InventoryService._consume_batches(product, quantity)

        new_quantity = previous_quantity - quantity
        InventoryService._write_quantity(inventory, product, new_quantity)

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

        product.refresh_from_db()
        NotificationService.check_stock_level(product)

        return new_quantity, cogs_cash, cogs_debt

    @staticmethod
    @transaction.atomic
    def adjust_stock(product, new_quantity, user=None, notes=""):
        """Set stock to a specific quantity (manual adjustment).

        Partiya qatlami ham bir vaqtda to'g'rilanadi, aks holda ombor qoldig'i
        va tannarx hisobi bir-biridan ajralib ketardi.
        """
        new_quantity = int(new_quantity)
        if new_quantity < 0:
            raise InventoryError("Miqdor manfiy bo'lishi mumkin emas.")

        inventory = InventoryService._lock_inventory(product)
        previous_quantity = inventory.quantity
        diff = new_quantity - previous_quantity

        if diff == 0:
            return new_quantity

        tx_type = TransactionType.ADJUSTMENT_IN if diff > 0 else TransactionType.ADJUSTMENT_OUT

        InventoryService._write_quantity(inventory, product, new_quantity)

        if diff > 0:
            leftover = InventoryService._release_batches(product, diff)
            if leftover > 0:
                InventoryBatch.objects.create(
                    product=product,
                    quantity=leftover,
                    current_quantity=leftover,
                    purchase_price=product.purchase_price,
                    payment_method=BatchPaymentMethod.CASH,
                    reference_id="ADJUSTMENT",
                )
        else:
            InventoryService._consume_batches(product, abs(diff))

        InventoryTransaction.objects.create(
            product=product,
            transaction_type=tx_type,
            quantity=abs(diff),
            previous_quantity=previous_quantity,
            new_quantity=new_quantity,
            reference_type="ADJUSTMENT",
            created_by=user,
            notes=notes or f"Qo'lda tuzatish: {previous_quantity} → {new_quantity}",
        )

        product.refresh_from_db()
        NotificationService.check_stock_level(product)

        return new_quantity

    @staticmethod
    @transaction.atomic
    def sync_batches_to_quantity(product):
        """Force ``Σ batch.current_quantity`` to match ``Inventory.quantity``.

        Ta'mirlash buyruqlari uchun: qoldiq to'g'ri, lekin partiyalar og'ib
        qolgan holatni tekislaydi. Farq qiymatini qaytaradi.
        """
        inventory = InventoryService._lock_inventory(product)
        batch_total = InventoryService.batch_total(product)
        diff = inventory.quantity - batch_total

        if diff == 0:
            return 0

        if diff > 0:
            leftover = InventoryService._release_batches(product, diff)
            if leftover > 0:
                InventoryBatch.objects.create(
                    product=product,
                    quantity=leftover,
                    current_quantity=leftover,
                    purchase_price=product.purchase_price,
                    payment_method=BatchPaymentMethod.CASH,
                    reference_id="RECONCILE",
                )
        else:
            InventoryService._consume_batches(product, abs(diff))

        return diff
