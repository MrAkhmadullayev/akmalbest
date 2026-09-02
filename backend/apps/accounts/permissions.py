"""
Role-based permission classes for DRF views.
"""
from rest_framework.permissions import BasePermission


class IsSuperAdmin(BasePermission):
    """Allows access only to super admin users."""
    message = "Faqat Super Admin ruxsat berilgan."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'SUPER_ADMIN'
        )


class IsAdmin(BasePermission):
    """Allows access to SUPER_ADMIN and ADMIN users."""
    message = "Faqat Admin ruxsat berilgan."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ('SUPER_ADMIN', 'ADMIN')
        )


class IsCashier(BasePermission):
    """Allows access to cashiers, admins and super admins."""
    message = "Kassir yoki Admin ruxsat berilgan."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ('SUPER_ADMIN', 'ADMIN', 'CASHIER')
        )


class IsWarehouseManager(BasePermission):
    """Allows access to warehouse managers, admins and super admins."""
    message = "Ombor mudiri yoki Admin ruxsat berilgan."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ('SUPER_ADMIN', 'ADMIN', 'WAREHOUSE_MANAGER')
        )


class IsAdminOrWarehouseManager(BasePermission):
    """Allows access to admins, super admins and warehouse managers."""
    message = "Admin yoki Ombor mudiri ruxsat berilgan."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ('SUPER_ADMIN', 'ADMIN', 'WAREHOUSE_MANAGER')
        )


class IsCashierOrAdmin(BasePermission):
    """Allows access to cashiers, admins and super admins."""
    message = "Kassir yoki Admin ruxsat berilgan."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ('SUPER_ADMIN', 'ADMIN', 'CASHIER')
        )
