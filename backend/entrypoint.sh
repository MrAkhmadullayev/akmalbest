#!/usr/bin/env bash
# =============================================================================
#  Konteyner entrypoint
#  - Postgres tayyor bo'lguncha kutadi
#  - RUN_MIGRATIONS=true bo'lsa migratsiya + collectstatic bajaradi
#    (faqat `backend` servisida true; celery worker/beat migratsiya qilmasligi
#     kerak — aks holda parallel migratsiya poygasi bo'ladi)
#  - Ixtiyoriy: superuser yaratadi
# =============================================================================
set -euo pipefail

log() { echo "[entrypoint] $*"; }

# ----------------------------- 1. DB'ni kutish -------------------------------
if [ "${USE_SQLITE:-False}" != "True" ] && [ -n "${DATABASE_HOST:-}" ]; then
  log "PostgreSQL kutilmoqda: ${DATABASE_HOST}:${DATABASE_PORT:-5432}"
  python - <<'PY'
import os, socket, sys, time

host = os.environ.get("DATABASE_HOST", "db")
port = int(os.environ.get("DATABASE_PORT", "5432"))
deadline = time.time() + 60

while time.time() < deadline:
    try:
        with socket.create_connection((host, port), timeout=3):
            print(f"[entrypoint] PostgreSQL tayyor ({host}:{port})")
            sys.exit(0)
    except OSError:
        time.sleep(1)

print(f"[entrypoint] XATO: PostgreSQL 60s ichida javob bermadi ({host}:{port})", file=sys.stderr)
sys.exit(1)
PY
fi

# --------------------- 2. Migratsiya + static (faqat web) --------------------
if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  log "Migratsiyalar bajarilmoqda..."
  python manage.py migrate --noinput

  log "Static fayllar yig'ilmoqda..."
  python manage.py collectstatic --noinput --clear

  if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
    log "Superuser tekshirilmoqda: ${DJANGO_SUPERUSER_USERNAME}"
    python manage.py shell <<'PY'
import os
from django.contrib.auth import get_user_model

User = get_user_model()
username = os.environ["DJANGO_SUPERUSER_USERNAME"]
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(
        username=username,
        email=os.environ.get("DJANGO_SUPERUSER_EMAIL") or "",
        password=os.environ["DJANGO_SUPERUSER_PASSWORD"],
    )
    print(f"[entrypoint] Superuser yaratildi: {username}")
else:
    print(f"[entrypoint] Superuser allaqachon mavjud: {username}")
PY
  fi
fi

# ------------------------- 3. Asosiy jarayonni ishga tushirish ---------------
log "Ishga tushmoqda: $*"
exec "$@"
