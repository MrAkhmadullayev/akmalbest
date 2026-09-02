#!/usr/bin/env bash
# =============================================================================
#  Production deploy — serverda ishlaydi (CI/CD ham shu skriptni chaqiradi)
#
#      ./scripts/deploy.sh [IMAGE_TAG]
#
#  Bosqichlar: image pull -> zero-downtime'ga yaqin restart -> health tekshiruv
#  -> muvaffaqiyatsiz bo'lsa avtomatik rollback (oldingi tag'ga qaytish).
# =============================================================================
set -euo pipefail

cd "$(dirname "$0")/.."

COMPOSE="docker compose -f docker-compose.prod.yml"
NEW_TAG="${1:-latest}"

log()  { printf '\n\033[1;32m==> %s\033[0m\n' "$*"; }
fail() { printf '\n\033[1;31m[XATO] %s\033[0m\n' "$*"; exit 1; }

[ -f .env ] || fail ".env fayl topilmadi"

DOMAIN="$(grep -E '^DOMAIN=' .env | cut -d= -f2- | tr -d '"' || true)"
[ -n "$DOMAIN" ] || fail ".env ichida DOMAIN belgilanmagan"

# --------------------------------------------------- 0. Sertifikat bootstrap
# Nginx konfiguratsiyasi ssl_certificate'ni talab qiladi va fayl bo'lmasa
# umuman start bo'lmaydi ("tovuq va tuxum"). Birinchi deploy'da hali
# Let's Encrypt sertifikati yo'q -> vaqtinchalik self-signed qo'yamiz,
# aks holda nginx crash-loop'ga tushib deploy rollback qiladi.
# Sertifikatlar `certbot_conf` NOMLI VOLUME ichida yashaydi (host papkasida emas),
# shuning uchun tekshirishni ham, yaratishni ham konteyner ichidan qilamiz.
CERT_FILE="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"
if ! $COMPOSE run --rm --entrypoint sh certbot -c "[ -f '$CERT_FILE' ]" >/dev/null 2>&1; then
  log "Sertifikat topilmadi — vaqtinchalik self-signed yaratilmoqda"
  log "MUHIM: deploy tugagach ./scripts/init-letsencrypt.sh ni ishga tushiring"
  $COMPOSE run --rm --entrypoint sh certbot -c "
    mkdir -p /etc/letsencrypt/live/$DOMAIN &&
    openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
      -keyout /etc/letsencrypt/live/$DOMAIN/privkey.pem \
      -out /etc/letsencrypt/live/$DOMAIN/fullchain.pem \
      -subj '/CN=$DOMAIN'" >/dev/null 2>&1 \
    || fail "Vaqtinchalik sertifikat yaratilmadi"
fi

# Joriy tagni rollback uchun saqlab qolamiz
PREV_TAG="$(grep -E '^IMAGE_TAG=' .env | cut -d= -f2- || echo latest)"
log "Joriy tag: ${PREV_TAG:-latest} -> yangi tag: $NEW_TAG"

# .env ichidagi IMAGE_TAG ni yangilash
if grep -qE '^IMAGE_TAG=' .env; then
  sed -i.bak "s|^IMAGE_TAG=.*|IMAGE_TAG=$NEW_TAG|" .env
else
  echo "IMAGE_TAG=$NEW_TAG" >> .env
fi

rollback() {
  log "ROLLBACK: $PREV_TAG ga qaytilmoqda"
  sed -i.bak "s|^IMAGE_TAG=.*|IMAGE_TAG=${PREV_TAG:-latest}|" .env
  $COMPOSE up -d --no-build
  rm -f .env.bak   # sirlar bilan nusxa diskda qolmasin
  fail "Deploy muvaffaqiyatsiz — eski versiya tiklandi"
}

# ------------------------------------------------------------ 1. Image pull
log "Image'lar tortilmoqda"
$COMPOSE pull backend frontend || rollback

# ------------------------------------------------------------- 2. Migratsiya
# backend konteyneri entrypoint'da migrate qiladi (RUN_MIGRATIONS=true),
# shuning uchun uni birinchi ko'taramiz va tayyor bo'lishini kutamiz.
log "Backend yangilanmoqda (migratsiyalar bilan)"
$COMPOSE up -d --no-build db redis || rollback
$COMPOSE up -d --no-build --force-recreate backend || rollback

log "Backend health kutilmoqda"
for i in $(seq 1 30); do
  if $COMPOSE exec -T backend curl -fsS http://127.0.0.1:8000/api/ready/ >/dev/null 2>&1; then
    log "Backend tayyor ($i s)"
    break
  fi
  [ "$i" -eq 30 ] && { $COMPOSE logs --tail=80 backend; rollback; }
  sleep 2
done

# ------------------------------------------------------ 3. Qolgan servislar
log "Frontend, Celery va Nginx yangilanmoqda"
$COMPOSE up -d --no-build celery_worker celery_beat frontend certbot || rollback

# Nginx MAJBURIY qayta yaratiladi: upstream'dagi `backend`/`frontend` nomlari
# faqat start paytida bir marta DNS'dan o'qiladi. Konteynerlar yangi IP oldi,
# nginx image'i esa o'zgarmagani uchun compose uni "up-to-date" deb tegmaydi
# -> nginx o'lik IP'ga uradi -> 502. Shuning uchun force-recreate.
log "Nginx qayta yaratilmoqda (upstream DNS yangilanishi uchun)"
$COMPOSE up -d --no-build --force-recreate nginx || rollback

# --------------------------------------------------------- 4. Smoke test
log "Smoke test"
sleep 5
$COMPOSE exec -T nginx nginx -t >/dev/null 2>&1 || rollback
$COMPOSE exec -T frontend curl -fsS http://127.0.0.1:3000/healthz >/dev/null 2>&1 || rollback

# Eng muhim tekshiruv: nginx ORQALI o'tadigan yo'l. Yuqoridagi ikkitasi
# konteynerlarni alohida tekshiradi, bu esa butun zanjirni.
# Host'dan uramiz (nginx:alpine ichida curl yo'q), -k chunki bootstrap
# bosqichida sertifikat self-signed bo'lishi mumkin.
for i in $(seq 1 10); do
  if curl -fsSk -H "Host: $DOMAIN" \
       https://127.0.0.1/api/health/ >/dev/null 2>&1; then
    log "Nginx orqali javob keldi"
    break
  fi
  [ "$i" -eq 10 ] && { $COMPOSE logs --tail=50 nginx; rollback; }
  sleep 3
done

# ------------------------------------------------------------ 5. Tozalash
log "Eski image'lar tozalanmoqda"
docker image prune -af --filter "until=168h" >/dev/null 2>&1 || true

rm -f .env.bak
log "DEPLOY MUVAFFAQIYATLI — tag: $NEW_TAG"
$COMPOSE ps
