"""Smena tafsilotlari endpointi testlari.

Asosiy talab: Smenalar tarixi sahifasidagi HAR BIR kartaning summasi,
o'sha karta bosilganda ochiladigan ro'yxatning jami summasi bilan AYNAN
teng bo'lishi kerak. Aks holda foydalanuvchi "karta 500 000 deydi, ro'yxat
480 000 chiqadi" degan holatga tushadi.
"""

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User, UserRole
from apps.customers.models import Customer
from apps.debts.models import Debt
from apps.debts.services import DebtService
from apps.expenses.models import Expense, ExpenseCategory
from apps.inventory.models import TransactionType
from apps.inventory.services import InventoryService
from apps.products.models import Category, Product
from apps.reports.models import ShiftReport
from apps.sales.models import PaymentMethod
from apps.sales.services import SaleService


class ShiftDetailsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="shift_admin",
            password="testpassword123",
            first_name="Smena",
            last_name="Admin",
            role=UserRole.SUPER_ADMIN,
        )
        self.category = Category.objects.create(name="Smena Kategoriya")
        self.product = Product.objects.create(
            name="Smena Mahsulot",
            barcode="SHIFT-1",
            category=self.category,
            purchase_price=Decimal("1000"),
            selling_price=Decimal("2000"),
        )
        InventoryService.increase_stock(
            product=self.product,
            quantity=200,
            transaction_type=TransactionType.PURCHASE,
            purchase_price=Decimal("1000"),
        )
        self.product.refresh_from_db()
        self.customer = Customer.objects.create(full_name="Smena Mijoz", phone="+998900000009")

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _sale(self, qty, method, paid=None, due=None):
        sale, _ = SaleService.create_sale(
            items_data=[{"product_id": self.product.id, "quantity": qty}],
            payment_method=method,
            cashier=self.user,
            customer=self.customer if method == PaymentMethod.DEBT else None,
            due_date=due,
            paid_amount=paid,
        )
        return sale

    def _build_shift(self):
        """Turli harakatlar qilib, smenani yopadi."""
        self._sale(3, PaymentMethod.CASH, paid=Decimal("100000"))
        self._sale(2, PaymentMethod.CARD)
        debt_sale = self._sale(4, PaymentMethod.DEBT, due="2030-01-01")
        returned = self._sale(5, PaymentMethod.CASH, paid=Decimal("100000"))
        SaleService.return_sale_item(returned.items.first(), 2, self.user)

        DebtService.make_payment(Debt.objects.get(sale=debt_sale), Decimal("3000"), "CASH", self.user)
        DebtService.make_payment(Debt.objects.get(sale=debt_sale), Decimal("2000"), "CARD", self.user)

        Expense.objects.create(
            title="Smena xarajati",
            amount=Decimal("7000"),
            expense_date=timezone.now().date(),
            category=ExpenseCategory.objects.create(name="Test xarajat"),
            created_by=self.user,
        )

        response = self.client.post("/api/reports/close-shift/")
        self.assertEqual(response.status_code, 200, response.content)
        return ShiftReport.objects.latest("closed_at")

    def _details(self, shift, kind):
        r = self.client.get(f"/api/reports/shifts/{shift.id}/details/", {"kind": kind})
        self.assertEqual(r.status_code, 200, r.content)
        return r.data

    def test_every_card_total_matches_its_detail_list(self):
        shift = self._build_shift()

        # karta maydoni -> endpoint turi
        pairs = [
            ("total_sales", "sales"),
            ("total_profit", "profit"),
            ("total_cash", "cash"),
            ("total_card", "card"),
            ("total_debt", "debt"),
            ("total_expenses", "expenses"),
            ("total_debt_payments_cash", "debt_payments_cash"),
            ("total_debt_payments_card", "debt_payments_card"),
            ("total_returns", "returns"),
        ]

        for field, kind in pairs:
            with self.subTest(kind=kind):
                card_value = getattr(shift, field)
                detail = self._details(shift, kind)
                self.assertEqual(
                    Decimal(detail["total"]),
                    card_value,
                    f"'{kind}' ro'yxati jami {detail['total']}, karta esa {card_value} ko'rsatyapti",
                )

    def test_expenses_detail_lists_the_expense(self):
        shift = self._build_shift()
        detail = self._details(shift, "expenses")

        self.assertEqual(detail["count"], 1)
        row = detail["results"][0]
        self.assertEqual(row["title"], "Smena xarajati")
        self.assertEqual(row["subtitle"], "Test xarajat")
        self.assertEqual(Decimal(row["amount"]), Decimal("7000"))

    def test_debt_payments_are_split_by_method(self):
        shift = self._build_shift()

        cash = self._details(shift, "debt_payments_cash")
        card = self._details(shift, "debt_payments_card")

        self.assertEqual(cash["count"], 1)
        self.assertEqual(Decimal(cash["total"]), Decimal("3000"))
        self.assertEqual(card["count"], 1)
        self.assertEqual(Decimal(card["total"]), Decimal("2000"))

    def test_returns_detail_lists_returned_sale(self):
        shift = self._build_shift()
        detail = self._details(shift, "returns")

        self.assertEqual(detail["count"], 1)
        self.assertEqual(Decimal(detail["results"][0]["amount"]), Decimal("4000"))  # 2 dona x 2000

    def test_cash_detail_includes_refund_as_negative(self):
        shift = self._build_shift()
        detail = self._details(shift, "cash")

        refunds = [r for r in detail["results"] if r["status"] == "REFUND"]
        self.assertEqual(len(refunds), 1)
        self.assertEqual(Decimal(refunds[0]["amount"]), Decimal("-4000"))

    def test_sales_detail_rows_link_to_the_sale(self):
        shift = self._build_shift()
        detail = self._details(shift, "sales")

        self.assertEqual(detail["count"], 4)
        for row in detail["results"]:
            self.assertTrue(row["link"].startswith("/sales/"))

    def test_unknown_kind_is_rejected(self):
        shift = self._build_shift()
        r = self.client.get(f"/api/reports/shifts/{shift.id}/details/", {"kind": "boshqa"})
        self.assertEqual(r.status_code, 400)

    def test_missing_shift_returns_404(self):
        r = self.client.get(
            "/api/reports/shifts/00000000-0000-0000-0000-000000000000/details/", {"kind": "sales"}
        )
        self.assertEqual(r.status_code, 404)
