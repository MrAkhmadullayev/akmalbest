from decimal import Decimal

from django.test import TestCase

from apps.accounts.models import User, UserRole
from apps.customers.models import Customer
from apps.debts.models import Debt, DebtStatus
from apps.inventory.exceptions import InsufficientStockError
from apps.inventory.models import Inventory, InventoryBatch, InventoryTransaction, TransactionType
from apps.inventory.services import InventoryService
from apps.products.models import Category, Product
from apps.sales.finance import aggregate_sales
from apps.sales.models import Payment, PaymentMethod, Sale, SaleItem, SaleStatus
from apps.sales.services import SaleService


class BaseStoreTestCase(TestCase):
    """Umumiy fixture: bitta mahsulot, 10 dona qoldiq, partiyasi bilan."""

    def setUp(self):
        self.cashier = User.objects.create_user(
            username="cashier_test",
            password="testpassword123",
            first_name="Kassir",
            last_name="Test",
            role=UserRole.CASHIER,
        )
        self.category = Category.objects.create(name="Aroq", description="Aroq mahsulotlari")
        self.product = Product.objects.create(
            name="Absolut Vodka 0.5L",
            barcode="7312040017072",
            category=self.category,
            volume=Decimal("0.5"),
            purchase_price=Decimal("85000.00"),
            selling_price=Decimal("110000.00"),
            min_stock=5,
            warning_stock=10,
            max_stock=100,
        )
        # Qoldiq faqat servis orqali kiritiladi — partiya ham yaraladi.
        InventoryService.increase_stock(
            product=self.product,
            quantity=10,
            transaction_type=TransactionType.PURCHASE,
            purchase_price=Decimal("85000.00"),
            notes="test boshlang'ich",
        )
        self.product.refresh_from_db()
        self.inventory = Inventory.objects.get(product=self.product)

    def assert_sources_consistent(self, product=None):
        """Uch manba (kesh / ombor / partiyalar) bir xilligini tekshiradi."""
        product = product or self.product
        product.refresh_from_db()
        inventory = Inventory.objects.get(product=product)
        batch_total = InventoryService.batch_total(product)

        self.assertEqual(
            product.current_stock, inventory.quantity, "Product.current_stock keshi Inventory bilan mos emas"
        )
        self.assertEqual(batch_total, inventory.quantity, "Partiyalar yig'indisi ombor qoldig'i bilan mos emas")


class StockIntegrityTests(BaseStoreTestCase):
    """Ombor hisobining yaxlitligi."""

    def test_fixture_is_consistent(self):
        self.assert_sources_consistent()
        self.assertEqual(self.inventory.quantity, 10)

    def test_sale_beyond_stock_is_rejected(self):
        with self.assertRaises(ValueError):
            SaleService.create_sale(
                items_data=[{"product_id": self.product.id, "quantity": 15}],
                payment_method=PaymentMethod.CASH,
                cashier=self.cashier,
                paid_amount=Decimal("2000000.00"),
            )

        self.assert_sources_consistent()
        self.assertEqual(Inventory.objects.get(product=self.product).quantity, 10)
        self.assertEqual(Sale.objects.count(), 0)
        self.assertEqual(SaleItem.objects.count(), 0)

    def test_duplicate_lines_cannot_oversell(self):
        """Bir mahsulot ikki qatorda kelsa ham qoldiq manfiyga tushmasligi kerak."""
        with self.assertRaises(ValueError):
            SaleService.create_sale(
                items_data=[
                    {"product_id": self.product.id, "quantity": 6},
                    {"product_id": self.product.id, "quantity": 6},
                ],
                payment_method=PaymentMethod.CASH,
                cashier=self.cashier,
                paid_amount=Decimal("5000000.00"),
            )

        self.assert_sources_consistent()
        self.assertEqual(Inventory.objects.get(product=self.product).quantity, 10)

    def test_duplicate_lines_are_merged(self):
        sale, _ = SaleService.create_sale(
            items_data=[
                {"product_id": self.product.id, "quantity": 2},
                {"product_id": self.product.id, "quantity": 3},
            ],
            payment_method=PaymentMethod.CASH,
            cashier=self.cashier,
            paid_amount=Decimal("1000000.00"),
        )

        self.assertEqual(sale.items.count(), 1, "Takroriy qatorlar bitta qatorga birlashishi kerak")
        self.assertEqual(sale.items.first().quantity, 5)
        self.assertEqual(Inventory.objects.get(product=self.product).quantity, 5)
        self.assert_sources_consistent()

    def test_decrease_stock_raises_typed_error(self):
        with self.assertRaises(InsufficientStockError):
            InventoryService.decrease_stock(
                product=self.product,
                quantity=99,
                transaction_type=TransactionType.SALE,
            )

    def test_adjust_stock_keeps_batches_in_sync(self):
        InventoryService.adjust_stock(product=self.product, new_quantity=25, user=self.cashier)
        self.assert_sources_consistent()
        self.assertEqual(Inventory.objects.get(product=self.product).quantity, 25)

        InventoryService.adjust_stock(product=self.product, new_quantity=4, user=self.cashier)
        self.assert_sources_consistent()
        self.assertEqual(Inventory.objects.get(product=self.product).quantity, 4)

    def test_inventory_row_created_for_new_product(self):
        product = Product.objects.create(
            name="Yangi mahsulot",
            barcode="1111111111111",
            category=self.category,
            purchase_price=Decimal("1000"),
            selling_price=Decimal("2000"),
        )
        self.assertTrue(Inventory.objects.filter(product=product).exists())

    def test_successful_sale_records_everything(self):
        sale, change = SaleService.create_sale(
            items_data=[{"product_id": self.product.id, "quantity": 3}],
            payment_method=PaymentMethod.CASH,
            cashier=self.cashier,
            paid_amount=Decimal("330000.00"),
        )

        self.assertEqual(sale.total, Decimal("330000.00"))
        self.assertEqual(change, Decimal("0.00"))
        self.assertEqual(sale.status, SaleStatus.COMPLETED)
        self.assertEqual(Inventory.objects.get(product=self.product).quantity, 7)
        self.assert_sources_consistent()

        item = SaleItem.objects.get(sale=sale)
        self.assertEqual(item.purchase_price_snapshot, Decimal("85000.00"))
        # Foyda = 3 × (110000 − 85000)
        self.assertEqual(sale.profit, Decimal("75000.00"))

        self.assertTrue(
            InventoryTransaction.objects.filter(
                product=self.product, transaction_type=TransactionType.SALE, quantity=3
            ).exists()
        )


class DiscountTests(BaseStoreTestCase):
    """Savdo darajasidagi chegirma qatorlarga to'g'ri taqsimlanishi."""

    def test_sale_discount_is_allocated_to_lines(self):
        sale, _ = SaleService.create_sale(
            items_data=[{"product_id": self.product.id, "quantity": 2}],
            payment_method=PaymentMethod.CASH,
            cashier=self.cashier,
            discount=Decimal("20000.00"),
            paid_amount=Decimal("300000.00"),
        )

        line_sum = sum(i.subtotal for i in sale.items.all())
        self.assertEqual(line_sum, sale.total, "Qatorlar yig'indisi savdo summasiga teng bo'lishi kerak")
        self.assertEqual(sale.total, Decimal("200000.00"))
        # Foyda chegirmani hisobga olishi kerak: 2×25000 − 20000
        self.assertEqual(sale.profit, Decimal("30000.00"))

    def test_discount_larger_than_total_is_rejected(self):
        with self.assertRaises(ValueError):
            SaleService.create_sale(
                items_data=[{"product_id": self.product.id, "quantity": 1}],
                payment_method=PaymentMethod.CASH,
                cashier=self.cashier,
                discount=Decimal("999999.00"),
                paid_amount=Decimal("0"),
            )

    def test_insufficient_cash_is_rejected(self):
        with self.assertRaises(ValueError):
            SaleService.create_sale(
                items_data=[{"product_id": self.product.id, "quantity": 1}],
                payment_method=PaymentMethod.CASH,
                cashier=self.cashier,
                paid_amount=Decimal("1000.00"),
            )
        self.assertEqual(Sale.objects.count(), 0)


class ReturnTests(BaseStoreTestCase):
    def _make_sale(self, quantity=4, payment_method=PaymentMethod.CASH, customer=None, due_date=None):
        sale, _ = SaleService.create_sale(
            items_data=[{"product_id": self.product.id, "quantity": quantity}],
            payment_method=payment_method,
            cashier=self.cashier,
            customer=customer,
            due_date=due_date,
            paid_amount=Decimal("5000000.00") if payment_method == PaymentMethod.CASH else None,
        )
        return sale

    def test_partial_return_restores_stock_and_money(self):
        sale = self._make_sale(quantity=4)
        item = sale.items.first()

        SaleService.return_sale_item(item, 1, self.cashier)

        sale.refresh_from_db()
        self.assertEqual(sale.status, SaleStatus.PARTIALLY_RETURNED)
        self.assertEqual(sale.returned_total, Decimal("110000.00"))
        self.assertEqual(sale.net_total, Decimal("330000.00"))
        self.assertEqual(Inventory.objects.get(product=self.product).quantity, 7)
        self.assert_sources_consistent()

        refunds = Payment.objects.filter(sale=sale, is_refund=True)
        self.assertEqual(refunds.count(), 1)
        self.assertEqual(refunds.first().amount, Decimal("110000.00"))

    def test_partially_returned_sale_still_counts_in_reports(self):
        """Eng jiddiy xato: qisman qaytarilgan savdo hisobotdan yo'qolib ketardi."""
        sale = self._make_sale(quantity=4)
        SaleService.return_sale_item(sale.items.first(), 1, self.cashier)

        summary = aggregate_sales(Sale.objects.all())
        self.assertEqual(summary["total_sales"], Decimal("330000.00"))
        self.assertEqual(summary["returned_total"], Decimal("110000.00"))
        self.assertEqual(summary["total_profit"], Decimal("75000.00"))

    def test_return_more_than_sold_is_rejected(self):
        sale = self._make_sale(quantity=2)
        with self.assertRaises(ValueError):
            SaleService.return_sale_item(sale.items.first(), 3, self.cashier)

    def test_piecemeal_returns_sum_exactly(self):
        """Bo'lak-bo'lak qaytarishda yaxlitlash qoldig'i yig'ilib qolmasligi kerak."""
        sale, _ = SaleService.create_sale(
            items_data=[{"product_id": self.product.id, "quantity": 3}],
            payment_method=PaymentMethod.CASH,
            cashier=self.cashier,
            discount=Decimal("10000.00"),
            paid_amount=Decimal("5000000.00"),
        )
        item = sale.items.first()

        SaleService.return_sale_item(item, 1, self.cashier)
        SaleService.return_sale_item(item, 1, self.cashier)
        SaleService.return_sale_item(item, 1, self.cashier)

        sale.refresh_from_db()
        self.assertEqual(sale.status, SaleStatus.RETURNED)
        self.assertEqual(sale.returned_total, sale.total, "To'liq qaytarishda summa aynan teng bo'lishi kerak")
        self.assertEqual(sale.net_total, Decimal("0.00"))
        self.assertEqual(Inventory.objects.get(product=self.product).quantity, 10)
        self.assert_sources_consistent()

        refund_total = sum(p.amount for p in Payment.objects.filter(sale=sale, is_refund=True))
        self.assertEqual(refund_total, sale.total)

    def test_return_restores_original_batch(self):
        sale = self._make_sale(quantity=4)
        SaleService.return_sale_item(sale.items.first(), 4, self.cashier)

        # Qaytarilgan tovar yangi partiya ochmasdan eskisiga qaytishi kerak.
        self.assertEqual(InventoryBatch.objects.filter(product=self.product).count(), 1)
        self.assert_sources_consistent()


class CancelSaleTests(BaseStoreTestCase):
    def test_cancel_cash_sale_restores_everything(self):
        sale, _ = SaleService.create_sale(
            items_data=[{"product_id": self.product.id, "quantity": 3}],
            payment_method=PaymentMethod.CASH,
            cashier=self.cashier,
            paid_amount=Decimal("330000.00"),
        )

        SaleService.cancel_sale(sale, self.cashier)

        sale.refresh_from_db()
        self.assertEqual(sale.status, SaleStatus.CANCELLED)
        self.assertEqual(Inventory.objects.get(product=self.product).quantity, 10)
        self.assert_sources_consistent()

        refund_total = sum(p.amount for p in Payment.objects.filter(sale=sale, is_refund=True))
        self.assertEqual(refund_total, sale.total)

    def test_cancelled_sale_is_excluded_from_revenue(self):
        sale, _ = SaleService.create_sale(
            items_data=[{"product_id": self.product.id, "quantity": 3}],
            payment_method=PaymentMethod.CASH,
            cashier=self.cashier,
            paid_amount=Decimal("330000.00"),
        )
        SaleService.cancel_sale(sale, self.cashier)

        summary = aggregate_sales(Sale.objects.all())
        self.assertEqual(summary["total_sales"], Decimal("0"))
        self.assertEqual(summary["total_profit"], Decimal("0"))

    def test_cancel_debt_sale_closes_the_debt(self):
        """Nasiya savdo bekor qilinsa mijoz qarzdor bo'lib qolmasligi kerak."""
        customer = Customer.objects.create(full_name="Test Mijoz", phone="+998900000000")
        sale, _ = SaleService.create_sale(
            items_data=[{"product_id": self.product.id, "quantity": 2}],
            payment_method=PaymentMethod.DEBT,
            cashier=self.cashier,
            customer=customer,
            due_date="2030-01-01",
        )

        debt = Debt.objects.get(sale=sale)
        self.assertEqual(debt.remaining_amount, Decimal("220000.00"))

        SaleService.cancel_sale(sale, self.cashier)

        debt.refresh_from_db()
        self.assertEqual(debt.remaining_amount, Decimal("0.00"))
        self.assertEqual(debt.status, DebtStatus.PAID)
        self.assertEqual(Inventory.objects.get(product=self.product).quantity, 10)
        self.assert_sources_consistent()

    def test_cancel_twice_is_rejected(self):
        sale, _ = SaleService.create_sale(
            items_data=[{"product_id": self.product.id, "quantity": 1}],
            payment_method=PaymentMethod.CASH,
            cashier=self.cashier,
            paid_amount=Decimal("110000.00"),
        )
        SaleService.cancel_sale(sale, self.cashier)
        with self.assertRaises(ValueError):
            SaleService.cancel_sale(sale, self.cashier)


class DebtReturnTests(BaseStoreTestCase):
    def test_return_after_partial_payment_refunds_overpayment(self):
        """Mijoz to'lab bo'lgan qism uchun tovar qaytarsa, ortiqcha pul qaytadi."""
        from apps.debts.services import DebtService

        customer = Customer.objects.create(full_name="To'lovchi", phone="+998900000001")
        sale, _ = SaleService.create_sale(
            items_data=[{"product_id": self.product.id, "quantity": 2}],
            payment_method=PaymentMethod.DEBT,
            cashier=self.cashier,
            customer=customer,
            due_date="2030-01-01",
        )
        debt = Debt.objects.get(sale=sale)

        # 220 000 dan 200 000 to'landi, qoldiq 20 000.
        DebtService.make_payment(debt, Decimal("200000.00"), "CASH", self.cashier)

        # Hammasini qaytaradi — 220 000 qaytarilishi kerak, undan 20 000 qarzdan,
        # qolgan 200 000 naqd.
        SaleService.return_sale_item(sale.items.first(), 2, self.cashier)

        debt.refresh_from_db()
        self.assertEqual(debt.remaining_amount, Decimal("0.00"))

        cash_refund = sum(p.amount for p in Payment.objects.filter(sale=sale, is_refund=True))
        self.assertEqual(cash_refund, Decimal("200000.00"))
        self.assert_sources_consistent()
