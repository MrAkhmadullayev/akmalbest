"""Debt URL configuration."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DebtViewSet, DebtPaymentCreateView, DebtPaymentViewSet

router = DefaultRouter()
router.register(r'debts', DebtViewSet, basename='debts')
router.register(r'debt-payments', DebtPaymentViewSet, basename='debt-payments')

urlpatterns = [
    path('debt-payments/create/', DebtPaymentCreateView.as_view(), name='debt-payment-create'),
    path('', include(router.urls)),
]
