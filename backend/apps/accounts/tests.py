"""Modul ruxsatlari (RBAC) testlari.

Bu testlar aynan bitta xato sinfini ushlab turadi: frontend ruxsat yuboradi,
backend uni JIMGINA tashlab yuboradi va foydalanuvchi "saqlandi" deb o'ylaydi.
DRF `ModelSerializer` tanimagan maydonlarni xatosiz yo'q qiladi, shuning uchun
bu yerda har bir maydon HAQIQATAN saqlanayotganini tekshiramiz.
"""

from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import MODULES, User, UserRole

STRONG_PASSWORD = "Qw8!zTr4vLm2"


class CacheIsolatedAPITestCase(APITestCase):
    """DRF throttling holati keshda saqlanadi va testlar orasida qolib ketadi.

    Bir testda sarflangan limit boshqasini yiqitmasligi uchun har safar
    keshni tozalaymiz.
    """

    def setUp(self):
        super().setUp()
        cache.clear()


class EffectivePermissionsTests(CacheIsolatedAPITestCase):
    """Model darajasidagi ruxsat hisob-kitobi."""

    def test_super_admin_gets_every_module(self):
        user = User.objects.create_user(
            username="boss",
            password=STRONG_PASSWORD,
            role=UserRole.SUPER_ADMIN,
        )
        self.assertEqual(user.effective_permissions, dict.fromkeys(MODULES, True))

    def test_role_defaults_apply_when_no_overrides(self):
        cashier = User.objects.create_user(
            username="kassir",
            password=STRONG_PASSWORD,
            role=UserRole.CASHIER,
        )
        perms = cashier.effective_permissions
        self.assertTrue(perms["pos"])
        self.assertFalse(perms["expenses"])
        self.assertFalse(perms["reports"])
        # Har doim barcha modullar uchun kalit bo'lishi kerak
        self.assertEqual(set(perms), set(MODULES))

    def test_overrides_beat_role_defaults_in_both_directions(self):
        cashier = User.objects.create_user(
            username="kassir2",
            password=STRONG_PASSWORD,
            role=UserRole.CASHIER,
            permissions={"reports": True, "pos": False},
        )
        perms = cashier.effective_permissions
        self.assertTrue(perms["reports"])
        self.assertFalse(perms["pos"])
        # Tegilmagan modullar rol standartida qoladi
        self.assertTrue(perms["customers"])

    def test_super_admin_ignores_negative_overrides(self):
        boss = User.objects.create_user(
            username="boss2",
            password=STRONG_PASSWORD,
            role=UserRole.SUPER_ADMIN,
            permissions={"reports": False},
        )
        self.assertTrue(boss.has_module_permission("reports"))


class UserApiPermissionsTests(CacheIsolatedAPITestCase):
    """Super admin foydalanuvchi yaratganda/tahrirlaganda maydonlar SAQLANADIMI."""

    def setUp(self):
        super().setUp()
        self.super_admin = User.objects.create_user(
            username="root",
            password=STRONG_PASSWORD,
            role=UserRole.SUPER_ADMIN,
        )
        self.client.force_authenticate(user=self.super_admin)
        self.list_url = reverse("users-list")

    def test_create_persists_permissions_and_is_active(self):
        response = self.client.post(
            self.list_url,
            {
                "username": "yangi",
                "first_name": "Yangi",
                "last_name": "Xodim",
                "role": UserRole.CASHIER,
                "is_active": False,
                "permissions": {"reports": True},
                "password": STRONG_PASSWORD,
                "password_confirm": STRONG_PASSWORD,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        created = User.objects.get(username="yangi")
        self.assertFalse(created.is_active)
        self.assertEqual(created.permissions, {"reports": True})
        self.assertTrue(created.has_module_permission("reports"))

    def test_update_persists_permissions_and_username(self):
        target = User.objects.create_user(
            username="eski",
            password=STRONG_PASSWORD,
            role=UserRole.CASHIER,
        )
        response = self.client.patch(
            reverse("users-detail", args=[target.id]),
            {"username": "yangilangan", "permissions": {"expenses": True}},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        target.refresh_from_db()
        self.assertEqual(target.username, "yangilangan")
        self.assertEqual(target.permissions, {"expenses": True})

    def test_update_can_change_password(self):
        target = User.objects.create_user(
            username="parolchi",
            password=STRONG_PASSWORD,
            role=UserRole.CASHIER,
        )
        new_password = "Zx9@bNq5wKt7"
        response = self.client.patch(
            reverse("users-detail", args=[target.id]),
            {"password": new_password, "password_confirm": new_password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        target.refresh_from_db()
        self.assertTrue(target.check_password(new_password))

    def test_update_without_password_keeps_old_one(self):
        target = User.objects.create_user(
            username="tegilmagan",
            password=STRONG_PASSWORD,
            role=UserRole.CASHIER,
        )
        response = self.client.patch(
            reverse("users-detail", args=[target.id]),
            {"first_name": "Yangi ism"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        target.refresh_from_db()
        self.assertTrue(target.check_password(STRONG_PASSWORD))

    def test_mismatched_passwords_are_rejected(self):
        target = User.objects.create_user(
            username="nomos",
            password=STRONG_PASSWORD,
            role=UserRole.CASHIER,
        )
        response = self.client.patch(
            reverse("users-detail", args=[target.id]),
            {"password": "Zx9@bNq5wKt7", "password_confirm": "boshqa"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_module_is_rejected_not_silently_dropped(self):
        response = self.client.patch(
            reverse("users-detail", args=[self.super_admin.id]),
            {"permissions": {"yoq_bunday_modul": True}},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # config.exceptions.custom_exception_handler javobni
        # {success, message, errors} ko'rinishiga o'rab beradi.
        self.assertIn("permissions", response.data["errors"])

    def test_me_endpoint_exposes_effective_permissions(self):
        response = self.client.get(reverse("auth-me"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(response.data["effective_permissions"]), set(MODULES))


class ModuleGuardTests(CacheIsolatedAPITestCase):
    """API haqiqatan to'sadimi — frontend menyusiga ishonmaymiz."""

    def setUp(self):
        super().setUp()
        self.cashier = User.objects.create_user(
            username="kassir3",
            password=STRONG_PASSWORD,
            role=UserRole.CASHIER,
        )
        self.client.force_authenticate(user=self.cashier)

    def test_cashier_cannot_open_sales_report(self):
        response = self.client.get(reverse("report-sales"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cashier_can_open_dashboard(self):
        response = self.client.get(reverse("report-dashboard"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_granting_reports_opens_the_endpoint(self):
        self.cashier.permissions = {"reports": True}
        self.cashier.save(update_fields=["permissions"])

        response = self.client.get(reverse("report-profit"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_revoking_a_default_module_closes_the_endpoint(self):
        self.cashier.permissions = {"customers": False}
        self.cashier.save(update_fields=["permissions"])

        response = self.client.get(reverse("customers-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cashier_cannot_reach_expenses(self):
        response = self.client.get(reverse("expenses-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
