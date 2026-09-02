#!/usr/bin/env bash
# =============================================================================
#  DigitalOcean Droplet — birinchi sozlash (Ubuntu 24.04)
#
#  Droplet'ga root sifatida kiring va bir marta ishga tushiring:
#     ssh root@SERVER_IP
#     curl -fsSL https://raw.githubusercontent.com/OWNER/REPO/main/scripts/server-setup.sh -o setup.sh
#     bash setup.sh deploy      # 'deploy' — yaratiladigan foydalanuvchi nomi
#
#  Nima qiladi:
#    1. Tizimni yangilaydi
#    2. Docker + Compose plugin o'rnatadi
#    3. Sudo huquqli non-root foydalanuvchi yaratadi (SSH kalitini ko'chiradi)
#    4. UFW firewall (22, 80, 443) va fail2ban
#    5. 2GB swap (kichik droplet'da build/OOM'ni oldini oladi)
#    6. Loyiha papkasi va backup cron
# =============================================================================
set -euo pipefail

DEPLOY_USER="${1:-deploy}"
APP_DIR="/opt/alkagol"

log()  { printf '\n\033[1;32m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m[!] %s\033[0m\n' "$*"; }

[ "$(id -u)" -eq 0 ] || { echo "root sifatida ishga tushiring"; exit 1; }

# ------------------------------------------------------------- 1. Yangilash
log "Tizim paketlari yangilanmoqda"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq ca-certificates curl gnupg git ufw fail2ban unattended-upgrades

# --------------------------------------------------------------- 2. Docker
if ! command -v docker >/dev/null 2>&1; then
  log "Docker o'rnatilmoqda"
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
else
  log "Docker allaqachon o'rnatilgan: $(docker --version)"
fi

# Docker log rotation (disk to'lib qolmasligi uchun)
cat > /etc/docker/daemon.json <<'JSON'
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "3" }
}
JSON
systemctl restart docker

# --------------------------------------------------- 3. Deploy foydalanuvchi
if ! id -u "$DEPLOY_USER" >/dev/null 2>&1; then
  log "Foydalanuvchi yaratilmoqda: $DEPLOY_USER"
  adduser --disabled-password --gecos "" "$DEPLOY_USER"
  usermod -aG sudo,docker "$DEPLOY_USER"
  echo "$DEPLOY_USER ALL=(ALL) NOPASSWD:ALL" > "/etc/sudoers.d/90-$DEPLOY_USER"
  chmod 440 "/etc/sudoers.d/90-$DEPLOY_USER"

  # root'ning SSH kalitlarini ko'chirish
  if [ -f /root/.ssh/authorized_keys ]; then
    mkdir -p "/home/$DEPLOY_USER/.ssh"
    cp /root/.ssh/authorized_keys "/home/$DEPLOY_USER/.ssh/authorized_keys"
    chown -R "$DEPLOY_USER:$DEPLOY_USER" "/home/$DEPLOY_USER/.ssh"
    chmod 700 "/home/$DEPLOY_USER/.ssh"
    chmod 600 "/home/$DEPLOY_USER/.ssh/authorized_keys"
  else
    warn "/root/.ssh/authorized_keys topilmadi — SSH kalitni qo'lda qo'shing!"
  fi
else
  log "Foydalanuvchi mavjud: $DEPLOY_USER"
  usermod -aG docker "$DEPLOY_USER"
fi

# ------------------------------------------------------------- 4. Firewall
log "UFW firewall sozlanmoqda"
ufw --force reset >/dev/null
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp   comment 'SSH'
ufw allow 80/tcp   comment 'HTTP'
ufw allow 443/tcp  comment 'HTTPS'
ufw --force enable
systemctl enable --now fail2ban

# SSH qattiqlashtirish
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/'   /etc/ssh/sshd_config
systemctl reload ssh || systemctl reload sshd || true

# ----------------------------------------------------------------- 5. Swap
if ! swapon --show | grep -q .; then
  log "2GB swap yaratilmoqda"
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile >/dev/null
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
  sysctl -w vm.swappiness=10 >/dev/null
  echo 'vm.swappiness=10' > /etc/sysctl.d/99-swappiness.conf
fi

# ------------------------------------------------------- 6. Loyiha papkasi
log "Loyiha papkasi: $APP_DIR"
mkdir -p "$APP_DIR"   # backups/ ni backup.sh o'zi yaratadi — git clone bo'sh papka talab qiladi
chown -R "$DEPLOY_USER:$DEPLOY_USER" "$APP_DIR"

# Avtomatik xavfsizlik yangilanishlari
dpkg-reconfigure -f noninteractive unattended-upgrades >/dev/null 2>&1 || true

# Cron: har kuni 03:00 da DB backup, har dushanba 04:00 da nginx reload (SSL)
CRON_FILE=/etc/cron.d/alkagol
cat > "$CRON_FILE" <<CRON
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
0 3 * * * $DEPLOY_USER cd $APP_DIR && ./scripts/backup.sh >> $APP_DIR/backups/backup.log 2>&1
0 4 * * 1 $DEPLOY_USER cd $APP_DIR && ./scripts/ssl-renew.sh >> $APP_DIR/backups/ssl.log 2>&1
CRON
chmod 644 "$CRON_FILE"

log "TAYYOR"
cat <<EOF

Keyingi qadamlar:
  1. Chiqing va yangi foydalanuvchi bilan kiring:
       ssh $DEPLOY_USER@<SERVER_IP>

  2. Reponi kloning qiling:
       git clone https://github.com/<OWNER>/<REPO>.git $APP_DIR
       cd $APP_DIR

  3. .env tayyorlang:
       cp .env.example .env && nano .env
       # SECRET_KEY:  openssl rand -base64 48
       # DOMAIN, POSTGRES_PASSWORD, IMAGE_OWNER ni to'ldiring

  4. GHCR'ga login (private repo bo'lsa):
       echo <GITHUB_PAT> | docker login ghcr.io -u <USERNAME> --password-stdin

  5. Ishga tushiring:
       docker compose -f docker-compose.prod.yml up -d

  6. Domen A-record serverga qarab turgach:
       ./scripts/init-letsencrypt.sh
EOF
