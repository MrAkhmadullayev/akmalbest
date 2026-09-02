#!/usr/bin/env bash
# =============================================================================
#  Sertifikatni yangilash + nginx reload (haftalik cron)
#  certbot konteyneri yangilaydi, lekin nginx yangi faylni o'qishi uchun
#  reload kerak.
# =============================================================================
set -euo pipefail

cd "$(dirname "$0")/.."
COMPOSE="docker compose -f docker-compose.prod.yml"

echo "[$(date '+%F %T')] certbot renew"
# --entrypoint MAJBURIY: prod compose'da certbot servisining entrypoint'i
# cheksiz sikl (`while :; do ... sleep 12h; done`). Uni almashtirmasak
# `run --rm` konteyneri hech qachon chiqmaydi va cron osilib qoladi.
$COMPOSE run --rm --entrypoint certbot certbot \
  renew --webroot -w /var/www/certbot --quiet || true

echo "[$(date '+%F %T')] nginx reload"
$COMPOSE exec -T nginx nginx -t && $COMPOSE exec -T nginx nginx -s reload

echo "[$(date '+%F %T')] tayyor"
