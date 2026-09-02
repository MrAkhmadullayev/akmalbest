#!/usr/bin/env bash
# =============================================================================
#  PostgreSQL backup — har kuni cron orqali (server-setup.sh o'rnatadi)
#
#      ./scripts/backup.sh
#
#  Natija: backups/alkagol_YYYY-MM-DD_HHMM.sql.gz
#  14 kundan eski nusxalar avtomatik o'chiriladi.
# =============================================================================
set -euo pipefail

cd "$(dirname "$0")/.."

COMPOSE="docker compose -f docker-compose.prod.yml"
BACKUP_DIR="./backups"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
STAMP="$(date +%Y-%m-%d_%H%M)"

[ -f .env ] || { echo "XATO: .env topilmadi"; exit 1; }

# .env ni `source` QILMAYMIZ: parolda probel, `$`, backtick yoki `!` bo'lsa bash
# qiymatni buzadi yoki hatto buyruq bajarib yuboradi (docker compose esa .env ni
# to'g'ri parse qiladi). Faqat kerakli kalitlarni tom ma'noda o'qiymiz.
env_get() {
  grep -m1 -E "^$1=" .env | cut -d= -f2- \
    | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//"
}
POSTGRES_USER="$(env_get POSTGRES_USER)"
POSTGRES_DB="$(env_get POSTGRES_DB)"

mkdir -p "$BACKUP_DIR"
FILE="$BACKUP_DIR/alkagol_${STAMP}.sql.gz"

echo "[$(date '+%F %T')] Backup boshlandi -> $FILE"

$COMPOSE exec -T db pg_dump \
  -U "${POSTGRES_USER:-alkagol_user}" \
  -d "${POSTGRES_DB:-alkagol_db}" \
  --clean --if-exists --no-owner --no-privileges \
  | gzip -9 > "$FILE"

SIZE="$(du -h "$FILE" | cut -f1)"

# Bo'sh/buzuq faylni saqlab qo'ymaymiz
if [ "$(stat -c%s "$FILE" 2>/dev/null || stat -f%z "$FILE")" -lt 1000 ]; then
  rm -f "$FILE"
  echo "[$(date '+%F %T')] XATO: backup juda kichik, o'chirildi"
  exit 1
fi

echo "[$(date '+%F %T')] Backup tayyor: $FILE ($SIZE)"

# Eski nusxalarni tozalash
find "$BACKUP_DIR" -name 'alkagol_*.sql.gz' -mtime "+$RETENTION_DAYS" -delete
echo "[$(date '+%F %T')] $RETENTION_DAYS kundan eski nusxalar o'chirildi"

# ---------------------------------------------------------------------------
# TIKLASH (restore):
#   gunzip -c backups/alkagol_2026-09-02_0300.sql.gz | \
#     docker compose -f docker-compose.prod.yml exec -T db \
#       psql -U alkagol_user -d alkagol_db
# ---------------------------------------------------------------------------
