"""Reports URL configuration."""
from django.urls import path

from .views import DashboardView, DebtReportView, InventoryReportView, ProfitReportView, SalesReportView

urlpatterns = [
    path('reports/dashboard/', DashboardView.as_view(), name='report-dashboard'),
    path('reports/sales/', SalesReportView.as_view(), name='report-sales'),
    path('reports/profit/', ProfitReportView.as_view(), name='report-profit'),
    path('reports/inventory/', InventoryReportView.as_view(), name='report-inventory'),
    path('reports/debts/', DebtReportView.as_view(), name='report-debts'),
]
