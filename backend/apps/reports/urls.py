"""Reports URL configuration."""

from django.urls import path

from .shift_details import ShiftDetailView
from .views import (
    CloseShiftView,
    DashboardView,
    DebtReportView,
    InventoryReportView,
    ProfitReportView,
    SalesReportView,
    ShiftListView,
)

urlpatterns = [
    path("reports/dashboard/", DashboardView.as_view(), name="report-dashboard"),
    path("reports/close-shift/", CloseShiftView.as_view(), name="report-close-shift"),
    path("reports/shifts/", ShiftListView.as_view(), name="report-shifts"),
    path(
        "reports/shifts/<uuid:shift_id>/details/",
        ShiftDetailView.as_view(),
        name="report-shift-details",
    ),
    path("reports/sales/", SalesReportView.as_view(), name="report-sales"),
    path("reports/profit/", ProfitReportView.as_view(), name="report-profit"),
    path("reports/inventory/", InventoryReportView.as_view(), name="report-inventory"),
    path("reports/debts/", DebtReportView.as_view(), name="report-debts"),
]
