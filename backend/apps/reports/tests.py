"""Smena va hisobot mantig'i testlari."""

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.customers.models import Customer
from apps.debts.models import Debt
from apps.debts.services import DebtService
from apps.expenses.models import Expense
from apps.inventory.models import TransactionType
from apps.inventory.services import InventoryService
from apps.inventory.valuation import stock_valuation
from apps.products.models import Category, Product
from apps.reports.shifts import current_shift_start, shift_querysets
from apps.sales.finance import cash_movement
from apps.sales.models import PaymentMethod, Sale
from apps.sales.services import SaleService


class ShiftCashTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="kassir_smena",
            password="testpassword123",
            first_name="Kassir",
            last_name="Smena",
            role=UserRole.CASHIER,
        )
        self.category = Category.objects.create(name="Pivo")
        self.product = Product.objects.create(
            name="Pivo 0.5",
            barcode="4780000000001",
            category=self.category,
            purchase_price=Decimal("7000"),
            selling_price=Decimal("12000"),
        )
        InventoryService.increase_stock(
            product=self.product,
            quantity=50,
            transaction_type=TransactionType.PURCHASE,
            purchase_price=Decimal("7000"),
        )
        self.product.refresh_from_db()

    def test_debt_payments_are_counted_in_shift_cash(self):
        """Nasiya to'lovi naqd kelgan — kassa hisobiga kirishi shart."""
        customer = Customer.objects.create(full_name="Qarzdor", phone="+998900000002")
        sale, _ = SaleService.create_sale(
            items_data=[{"product_id": self.product.id, "quantity": 5}],
            payment_method=PaymentMethod.DEBT,
            cashier=self.user,
            customer=customer,
            due_date="2030-01-01",
        )
        debt = Debt.objects.get(sale=sale)
        DebtService.make_payment(debt, Decimal("30000.00"), "CASH", self.user)

        shift_start = current_shift_start()
        _sales, expenses_qs, debt_payments_qs, payments_qs = shift_querysets(shift_start)
        cash = cash_movement(payments_qs, debt_payments_qs, expenses_qs)

        self.assertEqual(cash["debt_payments_cash"], Decimal("30000.00"))
        # Savdo nasiya bo'lgani uchun savdo naqdi nol, lekin kassada 30 000 bor.
        self.assertEqual(cash["cash_sales"], Decimal("0"))
        self.assertEqual(cash["expected_cash"], Decimal("30000.00"))

    def test_expenses_reduce_expected_cash(self):
        SaleService.create_sale(
            items_data=[{"product_id": self.product.id, "quantity": 5}],
            payment_method=PaymentMethod.CASH,
            cashier=self.user,
            paid_amount=Decimal("60000.00"),
        )
        Expense.objects.create(
            title="Yetkazib berish",
            amount=Decimal("15000.00"),
            expense_date=timezone.now().date(),
            created_by=self.user,
        )

        shift_start = current_shift_start()
        _sales, expenses_qs, debt_payments_qs, payments_qs = shift_querysets(shift_start)
        cash = cash_movement(payments_qs, debt_payments_qs, expenses_qs)

        self.assertEqual(cash["cash_sales"], Decimal("60000.00"))
        self.assertEqual(cash["expenses"], Decimal("15000.00"))
        self.assertEqual(cash["expected_cash"], Decimal("45000.00"))

    def test_refund_reduces_shift_cash(self):
        sale, _ = SaleService.create_sale(
            items_data=[{"product_id": self.product.id, "quantity": 5}],
            payment_method=PaymentMethod.CASH,
            cashier=self.user,
            paid_amount=Decimal("60000.00"),
        )
        SaleService.return_sale_item(sale.items.first(), 2, self.user)

        shift_start = current_shift_start()
        _sales, _expenses, debt_payments_qs, payments_qs = shift_querysets(shift_start)
        cash = cash_movement(payments_qs, debt_payments_qs, None)

        # 5 dona sotildi, 2 qaytdi → kassada 60000 − 24000 = 36000
        self.assertEqual(cash["cash_sales"], Decimal("36000.00"))
        self.assertEqual(cash["refunds_cash"], Decimal("24000.00"))


class ValuationTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Vino")
        self.product = Product.objects.create(
            name="Vino 0.75",
            barcode="4780000000002",
            category=self.category,
            purchase_price=Decimal("50000"),
            selling_price=Decimal("80000"),
        )

    def test_valuation_matches_batches(self):
        InventoryService.increase_stock(
            product=self.product,
            quantity=10,
            transaction_type=TransactionType.PURCHASE,
            purchase_price=Decimal("50000"),
            payment_method="CASH",
        )
        InventoryService.increase_stock(
            product=self.product,
            quantity=5,
            transaction_type=TransactionType.PURCHASE,
            purchase_price=Decimal("60000"),
            payment_method="DEBT",
        )
        self.product.refresh_from_db()

        valuation = stock_valuation()

        self.assertEqual(valuation["total_units"], 15)
        self.assertEqual(valuation["cash_value"], Decimal("500000"))
        self.assertEqual(valuation["debt_value"], Decimal("300000"))
        self.assertEqual(valuation["cost_value"], Decimal("800000"))
        # Chakana qiymat sotish narxi bo'yicha
        self.assertEqual(valuation["retail_value"], Decimal("1200000"))

    def test_fifo_uses_oldest_batch_first(self):
        user = User.objects.create_user(
            username="fifo_kassir", password="testpassword123", first_name="F", last_name="K", role=UserRole.CASHIER
        )
        InventoryService.increase_stock(
            product=self.product,
            quantity=2,
            transaction_type=TransactionType.PURCHASE,
            purchase_price=Decimal("50000"),
        )
        InventoryService.increase_stock(
            product=self.product,
            quantity=2,
            transaction_type=TransactionType.PURCHASE,
            purchase_price=Decimal("70000"),
        )
        self.product.refresh_from_db()

        sale, _ = SaleService.create_sale(
            items_data=[{"product_id": self.product.id, "quantity": 3}],
            payment_method=PaymentMethod.CASH,
            cashier=user,
            paid_amount=Decimal("240000.00"),
        )

        # Tannarx: 2×50000 + 1×70000 = 170000; tushum 3×80000 = 240000
        self.assertEqual(sale.total_cogs_cash, Decimal("170000.00"))
        self.assertEqual(sale.profit, Decimal("70000.00"))


class SaleNumberTests(TestCase):
    def test_sale_numbers_increment(self):
        prefix = timezone.now().strftime("%Y%m%d")
        first = SaleService.generate_sale_number()
        self.assertEqual(first, f"{prefix}-0001")

        user = User.objects.create_user(
            username="raqam_kassir", password="testpassword123", first_name="R", last_name="K", role=UserRole.CASHIER
        )
        Sale.objects.create(
            sale_number=first,
            cashier=user,
            subtotal=Decimal("0"),
            total=Decimal("0"),
            payment_method=PaymentMethod.CASH,
        )
        self.assertEqual(SaleService.generate_sale_number(), f"{prefix}-0002")
