"""
Custom User model with role-based access control.
"""
import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserRole(models.TextChoices):
    SUPER_ADMIN = 'SUPER_ADMIN', 'Super Admin'
    ADMIN = 'ADMIN', 'Admin'
    CASHIER = 'CASHIER', 'Kassir'
    WAREHOUSE_MANAGER = 'WAREHOUSE_MANAGER', 'Ombor mudiri'


class UserManager(BaseUserManager):
    """Custom user manager supporting email/username login."""

    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError("Foydalanuvchi nomi kiritilishi shart.")
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', UserRole.SUPER_ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom User model with role field."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, unique=True, db_index=True)
    # noqa DJ001: `null=True` matn maydonida ikkita "bo'sh" qiymat ('' va NULL)
    # hosil qiladi. Tuzatish uchun migratsiya kerak — MVP'dan keyin qilinadi.
    email = models.EmailField(max_length=255, blank=True, null=True)  # noqa: DJ001
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.CASHIER,
        db_index=True,
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'users'
        ordering = ['-created_at']
        verbose_name = 'Foydalanuvchi'
        verbose_name_plural = 'Foydalanuvchilar'

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_super_admin(self):
        return self.role == UserRole.SUPER_ADMIN

    @property
    def is_admin(self):
        return self.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN)

    @property
    def is_cashier(self):
        return self.role == UserRole.CASHIER

    @property
    def is_warehouse_manager(self):
        return self.role == UserRole.WAREHOUSE_MANAGER
