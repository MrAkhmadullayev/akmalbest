#!/usr/bin/env bash
# =============================================================================
#  Let's Encrypt sertifikatini BIRINCHI marta olish
#
#  Muammo: nginx SSL konfiguratsiya bilan ishga tushmaydi, chunki sertifikat
#  hali yo'q. Sertifikat esa nginx ishlamasa olinmaydi (ACME HTTP-01).
#  Yechim: avval soxta (self-signed) sertifikat qo'yamiz -> nginx ko'tariladi
#  -> certbot haqiqiysini oladi -> nginx reload.
#
#  Ishlatish (loyiha papkasida, .env to'ldirilgan holda):
#      ./scripts/init-letsencrypt.sh
#
#  SHART: DOMAIN ning A-record'i shu serverning IP'siga qarab turishi kerak.
# =============================================================================
set -euo pipefail

cd "$(dirname "$0")/.."

COMPOSE="docker compose -f docker-compose.prod.yml"

[ -f .env ] || { echo "XATO: .env fayl topilmadi. cp .env.example .env"; exit 1; }

# .env ni `source` QILMAYMIZ — maxsus belgili parol bash'da buyruq bajarib
# yuborishi mumkin. Faqat kerakli kalitlarni tom ma'noda o'qiymiz.
env_get() {
  grep -m1 -E "^$1=" .env | cut -d= -f2- \
    | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//"
}
DOMAIN="$(env_get DOMAIN)"
ACME_EMAIL="$(env_get ACME_EMAIL)"

: "${DOMAIN:?.env ichida DOMAIN belgilanishi shart}"
: "${ACME_EMAIL:?.env ichida ACME_EMAIL belgilanishi shart}"

STAGING="${STAGING:-0}"   # STAGING=1 -> test sertifikat (rate limitga tushmaslik uchun)
RSA_KEY_SIZE=4096
CERT_PATH="/etc/letsencrypt/live/$DOMAIN"

log() { printf '\n\033[1;32m==> %s\033[0m\n' "$*"; }

# ---------------------------------------------------- 0. DNS tekshiruvi
log "DNS tekshirilmoqda: $DOMAIN"
SERVER_IP="$(curl -fsS https://ifconfig.me || echo '')"
DOMAIN_IP="$(getent hosts "$DOMAIN" | awk '{print $1}' | head -1 || echo '')"
if [ -n "$SERVER_IP" ] && [ -n "$DOMAIN_IP" ] && [ "$SERVER_IP" != "$DOMAIN_IP" ]; then
  echo "OGOHLANTIRISH: $DOMAIN -> $DOMAIN_IP, lekin server IP -> $SERVER_IP"
  read -rp "Davom etamizmi? (ha/yo'q) " ans
  [ "$ans" = "ha" ] || exit 1
fi

# ------------------------------------- 1. TLS parametrlarini yuklab olish
log "TLS parametrlari tayyorlanmoqda"
$COMPOSE run --rm --entrypoint "/bin/sh -c '\
  mkdir -p /etc/letsencrypt && \
  [ -f /etc/letsencrypt/options-ssl-nginx.conf ] || \
    wget -qO /etc/letsencrypt/options-ssl-nginx.conf https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf; \
  [ -f /etc/letsencrypt/ssl-dhparams.pem ] || \
    wget -qO /etc/letsencrypt/ssl-dhparams.pem https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem'" \
  certbot || true

# ------------------------------------------- 2. Vaqtinchalik soxta sertifikat
log "Vaqtinchalik self-signed sertifikat yaratilmoqda"
$COMPOSE run --rm --entrypoint "/bin/sh -c '\
  mkdir -p $CERT_PATH && \
  openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
    -keyout $CERT_PATH/privkey.pem \
    -out $CERT_PATH/fullchain.pem \
    -subj \"/CN=localhost\"'" certbot

# ----------------------------------------------------- 3. Nginx'ni ko'tarish
log "Nginx ishga tushirilmoqda"
$COMPOSE up -d nginx
sleep 5

# ----------------------------------- 4. Soxta sertifikatni olib tashlash
log "Soxta sertifikat o'chirilmoqda"
$COMPOSE run --rm --entrypoint "/bin/sh -c '\
  rm -rf /etc/letsencrypt/live/$DOMAIN \
         /etc/letsencrypt/archive/$DOMAIN \
         /etc/letsencrypt/renewal/$DOMAIN.conf'" certbot

# ------------------------------------------------ 5. Haqiqiy sertifikat
log "Let's Encrypt sertifikati so'ralmoqda"
STAGING_ARG=""
[ "$STAGING" != "0" ] && STAGING_ARG="--staging"

# www subdomeni uchun A-record bo'lmasa uni SO'RAMAYMIZ: certbot bitta domen
# tekshiruvdan o'tmasa butun so'rovni bekor qiladi va muvaffaqiyatsiz
# urinishlar Let's Encrypt limitiga (haftasiga 5 ta) yoziladi.
DOMAIN_ARGS="-d $DOMAIN"
if getent hosts "www.$DOMAIN" >/dev/null 2>&1; then
  DOMAIN_ARGS="$DOMAIN_ARGS -d www.$DOMAIN"
  log "www.$DOMAIN topildi — sertifikatga qo'shiladi"
else
  log "www.$DOMAIN uchun DNS yozuvi yo'q — o'tkazib yuborildi"
fi

$COMPOSE run --rm --entrypoint "\
  certbot certonly --webroot -w /var/www/certbot \
    $STAGING_ARG \
    --email $ACME_EMAIL \
    $DOMAIN_ARGS \
    --rsa-key-size $RSA_KEY_SIZE \
    --agree-tos \
    --no-eff-email \
    --force-renewal" certbot

# ------------------------------------------------------- 6. Nginx reload
log "Nginx qayta yuklanmoqda"
$COMPOSE exec -T nginx nginx -s reload

log "TAYYOR — https://$DOMAIN"
echo "Tekshirish: curl -I https://$DOMAIN"
