from decimal import Decimal

from django.test import TestCase

from apps.accounts.models import User, UserRole
from apps.inventory.models import Inventory, InventoryTransaction, TransactionType
from apps.products.models import Category, Product
from apps.sales.models import PaymentMethod, Sale, SaleItem, SaleStatus
from apps.sales.services import SaleService


class AlkagolBusinessLogicTests(TestCase):

    def setUp(self):
        # Create user
        self.cashier = User.objects.create_user(
            username='cashier_test',
            password='testpassword123',
            first_name='Kassir',
            last_name='Test',
            role=UserRole.CASHIER
        )

        # Create Category
        self.category = Category.objects.create(name='Aroq', description='Aroq mahsulotlari')

        # Create Product
        self.product = Product.objects.create(
            name='Absolut Vodka 0.5L',
            barcode='7312040017072',
            category=self.category,
            volume=Decimal('0.5'),
            purchase_price=Decimal('85000.00'),
            selling_price=Decimal('110000.00'),
            current_stock=10,
            min_stock=5,
            warning_stock=10,
            max_stock=100
        )

        # Create Inventory
        self.inventory = Inventory.objects.create(
            product=self.product,
            quantity=10
        )

    def test_stock_validation_prevents_negative_stock(self):
        """Test that checkout fails and rollbacks if requested quantity exceeds current stock."""
        items_data = [
            {
                'product_id': self.product.id,
                'quantity': 15,  # Exceeds current_stock of 10
            }
        ]

        with self.assertRaises(ValueError):
            SaleService.create_sale(
                items_data=items_data,
                payment_method=PaymentMethod.CASH,
                cashier=self.cashier,
                paid_amount=Decimal('2000000.00')
            )

        # Check inventory is untouched
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 10)

        # Verify no Sale or SaleItem records were created
        self.assertEqual(Sale.objects.count(), 0)
        self.assertEqual(SaleItem.objects.count(), 0)

    def test_successful_sale_decreases_stock_and_creates_records(self):
        """Test that a valid sale creates Sale, SaleItem, Payment, and decreases stock."""
        items_data = [
            {
                'product_id': self.product.id,
                'quantity': 3,
            }
        ]

        sale, change_amount = SaleService.create_sale(
            items_data=items_data,
            payment_method=PaymentMethod.CASH,
            cashier=self.cashier,
            paid_amount=Decimal('330000.00')
        )

        # Assert Sale totals
        self.assertEqual(sale.subtotal, Decimal('330000.00'))
        self.assertEqual(sale.total, Decimal('330000.00'))
        self.assertEqual(sale.payment_method, PaymentMethod.CASH)
        self.assertEqual(sale.status, SaleStatus.COMPLETED)
        self.assertEqual(change_amount, Decimal('0.00'))

        # Assert Inventory decrease
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 7)

        # Assert snapshotting
        sale_item = SaleItem.objects.get(sale=sale)
        self.assertEqual(sale_item.product_name_snapshot, 'Absolut Vodka 0.5L')
        self.assertEqual(sale_item.purchase_price_snapshot, Decimal('85000.00'))
        self.assertEqual(sale_item.selling_price_snapshot, Decimal('110000.00'))

        # Assert inventory transaction record
        self.assertTrue(
            InventoryTransaction.objects.filter(
                product=self.product,
                transaction_type=TransactionType.SALE,
                quantity=3
            ).exists()
        )
