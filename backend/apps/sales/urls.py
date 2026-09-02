"""Sale URL configuration."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SaleViewSet, PaymentViewSet

router = DefaultRouter()
router.register(r'sales', SaleViewSet, basename='sales')
router.register(r'payments', PaymentViewSet, basename='payments')

urlpatterns = [path('', include(router.urls))]
