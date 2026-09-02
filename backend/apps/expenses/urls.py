"""Expense URL configuration."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ExpenseViewSet, ExpenseCategoryViewSet

router = DefaultRouter()
router.register(r'expenses', ExpenseViewSet, basename='expenses')
router.register(r'expense-categories', ExpenseCategoryViewSet, basename='expense-categories')
urlpatterns = [path('', include(router.urls))]
