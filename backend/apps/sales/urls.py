"""Sale URL configuration."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PaymentViewSet, SaleViewSet

router = DefaultRouter()
router.register(r'sales', SaleViewSet, basename='sales')
router.register(r'payments', PaymentViewSet, basename='payments')

urlpatterns = [path('', include(router.urls))]
