"""
Root URL configuration for Alkagol Store Management System.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from config.health import health, ready

urlpatterns = [
    # Admin panel manzili env orqali o'zgartiriladi (bot-scannerlarga qarshi)
    path(f'{settings.ADMIN_URL}/', admin.site.urls),

    # Health probes (Docker healthcheck / nginx / CI smoke test)
    path('api/health/', health, name='health'),
    path('api/ready/', ready, name='ready'),

    # API endpoints
    path('api/auth/', include('apps.accounts.urls')),
    path('api/', include('apps.products.urls')),
    path('api/', include('apps.inventory.urls')),
    path('api/', include('apps.suppliers.urls')),
    path('api/', include('apps.customers.urls')),
    path('api/', include('apps.sales.urls')),
    path('api/', include('apps.debts.urls')),
    path('api/', include('apps.expenses.urls')),
    path('api/', include('apps.reports.urls')),
    path('api/', include('apps.notifications.urls')),
    path('api/', include('apps.audit.urls')),
]

# Swagger/OpenAPI — prod'da ENABLE_API_DOCS=False bilan o'chirib qo'yish mumkin
if settings.ENABLE_API_DOCS:
    urlpatterns += [
        path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
        path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
