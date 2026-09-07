"""Mahsulot API testlari.

Asosiy regressiya: mahsulot yaratish 201 qaytarib, bazaga YOZILMAY qolgan edi.
Sabab — audit yozuvi UUID'ni JSON'ga aylantira olmay xato bergan, xato yutilgan,
lekin ulanish "rollback kerak" deb belgilangani uchun butun tranzaksiya jimgina
bekor bo'lgan.
"""

from decimal import Decimal

from django.db import transaction
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User, UserRole
from apps.audit.models import AuditLog
from apps.audit.services import AuditService
from apps.inventory.models import Inventory
from apps.products.models import Category, Product
from apps.products.serializers import ProductDetailSerializer


class ProductCreateApiTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="product_admin",
            password="testpassword123",
            first_name="Admin",
            last_name="Test",
            role=UserRole.SUPER_ADMIN,
        )
        self.category = Category.objects.create(name="Test Kategoriya")
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def _payload(self, **overrides):
        data = {
            "name": "Yangi Mahsulot",
            "barcode": "TEST-CREATE-1",
            "category": str(self.category.id),
            "volume": "0.50",
            "unit": "bottle",
            "purchase_price": "1000",
            "selling_price": "1500",
            "min_stock": 5,
            "warning_stock": 10,
            "max_stock": 100,
            "initial_stock": 12,
            "payment_method": "CASH",
            "is_active": True,
        }
        data.update(overrides)
        return data

    def test_created_product_is_actually_persisted(self):
        """201 qaytgan bo'lsa, mahsulot BAZADA ham bo'lishi shart."""
        response = self.client.post("/api/products/", self._payload(), format="json")

        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(
            Product.objects.filter(barcode="TEST-CREATE-1").exists(),
            "201 qaytdi, lekin mahsulot bazaga yozilmadi",
        )

    def test_created_product_appears_in_list_and_search(self):
        self.client.post("/api/products/", self._payload(), format="json")

        listed = self.client.get("/api/products/", {"search": "Yangi Mahsulot"})
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.data["count"], 1, "Yaratilgan mahsulot qidiruvda chiqmadi")

    def test_initial_stock_is_applied(self):
        self.client.post("/api/products/", self._payload(), format="json")

        product = Product.objects.get(barcode="TEST-CREATE-1")
        inventory = Inventory.objects.get(product=product)
        self.assertEqual(product.current_stock, 12)
        self.assertEqual(inventory.quantity, 12)

    def test_multipart_create_works(self):
        """Frontend multipart/form-data yuboradi."""
        response = self.client.post(
            "/api/products/", self._payload(is_active="true"), format="multipart"
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(Product.objects.filter(barcode="TEST-CREATE-1").exists())

    def test_audit_entry_is_written_for_create(self):
        self.client.post("/api/products/", self._payload(), format="json")
        self.assertTrue(
            AuditLog.objects.filter(model_name="Product", action="CREATE").exists(),
            "Audit yozuvi yaratilmadi",
        )


class AuditIsolationTests(TestCase):
    """Audit yozuvi hech qachon chaqiruvchi tranzaksiyani buzmasligi kerak."""

    def setUp(self):
        self.category = Category.objects.create(name="Audit Kategoriya")

    def test_serializer_payload_with_uuid_is_stored(self):
        """ProductDetailSerializer natijasida UUID bor — u ham saqlanishi kerak."""
        product = Product.objects.create(
            name="Audit Test",
            barcode="AUDIT-1",
            category=self.category,
            purchase_price=Decimal("1000"),
            selling_price=Decimal("1500"),
        )
        AuditService.log(
            user=None,
            action="CREATE",
            model_name="Product",
            object_id=str(product.id),
            new_data=ProductDetailSerializer(product).data,
        )
        entry = AuditLog.objects.get(model_name="Product", object_id=str(product.id))
        self.assertEqual(entry.new_data["barcode"], "AUDIT-1")
        # UUID matnga aylantirilgan bo'lishi kerak
        self.assertEqual(entry.new_data["category"], str(self.category.id))

    def test_failing_audit_does_not_roll_back_caller(self):
        """Audit yiqilsa ham, chaqiruvchi amal saqlanib qolishi shart."""

        class Unserializable:
            def __repr__(self):
                raise RuntimeError("bu obyekt umuman ifodalanmaydi")

        with transaction.atomic():
            product = Product.objects.create(
                name="Rollback Test",
                barcode="AUDIT-2",
                category=self.category,
                purchase_price=Decimal("1000"),
                selling_price=Decimal("1500"),
            )
            # object_id juda uzun -> INSERT xato beradi (max_length=255 kesiladi,
            # shuning uchun model_name orqali chegaradan chiqaramiz)
            AuditService.log(
                user=None,
                action="CREATE",
                model_name="X" * 500,  # max_length=100 -> DataError
                object_id=str(product.id),
                new_data={"ok": True},
            )

        self.assertTrue(
            Product.objects.filter(barcode="AUDIT-2").exists(),
            "Audit xatosi asosiy amalni bekor qilib yubordi",
        )
