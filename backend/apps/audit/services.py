"""Audit service for logging important actions."""
from .models import AuditLog


class AuditService:
    """Centralized audit logging."""

    @staticmethod
    def log(user, action, model_name, object_id='', old_data=None, new_data=None, ip_address=None):
        """Create an audit log entry."""
        try:
            AuditLog.objects.create(
                user=user,
                action=action,
                model_name=model_name,
                object_id=str(object_id),
                old_data=old_data,
                new_data=new_data,
                ip_address=ip_address,
            )
        except Exception:
            # Audit logging should never break the main flow
            pass
