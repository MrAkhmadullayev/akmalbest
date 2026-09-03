"""
Health-check endpointlari.

- /api/health/  -> liveness: jarayon tirikmi? (tashqi bog'liqliklarga tegmaydi)
- /api/ready/   -> readiness: DB va cache javob beryaptimi? Docker healthcheck,
                   nginx upstream va CI smoke-test shu yerga qaraydi.

Ikkalasi ham AllowAny — load balancer token bilan kelmaydi.

@throttle_classes([]) MAJBURIY: global AnonRateThrottle 10/min. Docker
healthcheck har 30 s da, deploy.sh esa 60 s ichida 30 martagacha uradi va
konteyner ichidan kelgan so'rovlarda X-Forwarded-For yo'q — hammasi bitta
127.0.0.1 bucket'ini bo'lishadi. Throttle o'chirilmasa 429 kela boshlaydi,
konteyner "unhealthy" bo'ladi va deploy rollback qiladi.
"""

from django.core.cache import cache
from django.db import connection
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
    throttle_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@extend_schema(tags=["health"], summary="Liveness probe")
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([])
def health(request):
    return Response({"status": "ok"})


@extend_schema(tags=["health"], summary="Readiness probe (DB + cache)")
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([])
def ready(request):
    checks = {}
    healthy = True

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["database"] = f"error: {exc.__class__.__name__}"
        healthy = False

    try:
        cache.set("__healthcheck__", 1, 5)
        checks["cache"] = "ok" if cache.get("__healthcheck__") == 1 else "error: no roundtrip"
        healthy = healthy and checks["cache"] == "ok"
    except Exception as exc:  # noqa: BLE001
        checks["cache"] = f"error: {exc.__class__.__name__}"
        healthy = False

    return Response(
        {"status": "ready" if healthy else "degraded", "checks": checks},
        status=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
    )
