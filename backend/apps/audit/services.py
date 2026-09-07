"""Audit service for logging important actions."""

import json
import logging

from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction

from .models import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """Centralized audit logging."""

    @staticmethod
    def _jsonify(value):
        """Convert a payload into something a JSONField can actually store.

        Serializer natijasida UUID, Decimal, date kabi turlar bo'ladi —
        ular standart JSON kodlovchisi uchun yaroqsiz. Masalan
        ``ProductDetailSerializer(...).data`` dagi ``category`` maydoni UUID
        obyekti bo'lib keladi va yozuv "Object of type UUID is not JSON
        serializable" xatosi bilan yiqilardi.
        """
        if value is None:
            return None
        try:
            return json.loads(json.dumps(value, cls=DjangoJSONEncoder, default=str))
        except (TypeError, ValueError):
            return {"__unserializable__": str(value)[:2000]}

    @staticmethod
    def log(user, action, model_name, object_id="", old_data=None, new_data=None, ip_address=None):
        """Create an audit log entry.

        Audit yozuvi HECH QACHON asosiy amalni buzmasligi kerak. Shuning uchun
        ikki qatlamli himoya bor:

        1. ``transaction.atomic()`` — alohida savepoint. Busiz, audit
           INSERT'i xato bersa, ulanish "rollback kerak" deb belgilanadi va
           chaqiruvchi tranzaksiya (masalan mahsulot yaratish) OXIRIDA
           jimgina bekor bo'lardi — API esa 201 qaytaraverardi.
        2. ``except`` — qolgan har qanday xato yutiladi, lekin endi
           JIMGINA emas: jurnalga yoziladi, aks holda muammo yashirin qoladi.
        """
        try:
            with transaction.atomic():
                AuditLog.objects.create(
                    user=user,
                    action=action,
                    model_name=model_name,
                    object_id=str(object_id)[:255],
                    old_data=AuditService._jsonify(old_data),
                    new_data=AuditService._jsonify(new_data),
                    ip_address=ip_address,
                )
        except Exception:
            logger.exception(
                "Audit yozuvini saqlab bo'lmadi (action=%s, model=%s, object_id=%s)",
                action,
                model_name,
                object_id,
            )
