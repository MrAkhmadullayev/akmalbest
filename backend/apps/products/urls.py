"""
Product URL configuration.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BrandViewSet, CategoryViewSet, ProductBarcodeLookupView, ProductViewSet

router = DefaultRouter()
router.register(r"categories", CategoryViewSet, basename="categories")
router.register(r"brands", BrandViewSet, basename="brands")
router.register(r"products", ProductViewSet, basename="products")

urlpatterns = [
    path("products/barcode/<str:barcode>/", ProductBarcodeLookupView.as_view(), name="product-barcode-lookup"),
    path("", include(router.urls)),
]
