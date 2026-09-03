"""Debt URL configuration."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DebtPaymentCreateView, DebtPaymentViewSet, DebtViewSet

router = DefaultRouter()
router.register(r"debts", DebtViewSet, basename="debts")
router.register(r"debt-payments", DebtPaymentViewSet, basename="debt-payments")

urlpatterns = [
    path("debt-payments/create/", DebtPaymentCreateView.as_view(), name="debt-payment-create"),
    path("", include(router.urls)),
]
