#!/usr/bin/env bash
# =============================================================================
#  Server birinchi sozlash (Ubuntu 22.04/24.04)
#  AWS EC2, DigitalOcean, Hetzner — farqi yo'q, hammasida ishlaydi.
#
#  AWS EC2 (Ubuntu AMI'da root bilan kirib bo'lmaydi, `ubuntu` useri bor):
#     scp -i ~/.ssh/id_ed25519 scripts/server-setup.sh ubuntu@<IP>:/tmp/
#     ssh -i ~/.ssh/id_ed25519 ubuntu@<IP>
#     sudo bash /tmp/server-setup.sh ubuntu
#
#  Root bilan kiriladigan serverlarda (DigitalOcean/Hetzner):
#     scp scripts/server-setup.sh root@<IP>:/root/
#     ssh root@<IP> "bash /root/server-setup.sh deploy"
#
#  Argument = deploy foydalanuvchi nomi. Mavjud bo'lsa (EC2'dagi `ubuntu`)
#  faqat docker guruhiga qo'shiladi, yangi bo'lsa to'liq yaratiladi.
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

  # SSH kalitlarini ko'chirish.
  #
  # DIQQAT (AWS EC2): u yerda /root/.ssh/authorized_keys BO'SH EMAS, lekin
  # ichida haqiqiy kalit o'rniga quyidagicha qator turadi:
  #     command="echo 'Please login as the user \"ubuntu\"...'" ssh-rsa AAAA...
  # Shu faylni ko'r-ko'rona nusxalasak, yangi foydalanuvchiga kirganda ham
  # o'sha xabar chiqib SSH darhol uziladi — server'ga umuman kira olmaysiz.
  # Shuning uchun avval bulut foydalanuvchisining faylini qidiramiz, topilmasa
  # root'nikini olamiz va `command="..."` prefiksini kesib tashlaymiz.
  SRC_KEYS=""
  for candidate in /home/ubuntu/.ssh/authorized_keys \
                   /home/ec2-user/.ssh/authorized_keys \
                   /home/admin/.ssh/authorized_keys \
                   /root/.ssh/authorized_keys; do
    if [ -s "$candidate" ]; then SRC_KEYS="$candidate"; break; fi
  done

  if [ -n "$SRC_KEYS" ]; then
    log "SSH kalitlar manbai: $SRC_KEYS"
    mkdir -p "/home/$DEPLOY_USER/.ssh"
    # Har qanday `command="..."` / `no-port-forwarding,...` prefiksini olib
    # tashlaymiz — faqat `ssh-` yoki `ecdsa-` dan boshlanadigan qismni qoldiramiz.
    sed -E 's/^.*(ssh-(rsa|ed25519|dss)|ecdsa-sha2-[a-z0-9-]+) /\1 /' "$SRC_KEYS" \
      | grep -E '^(ssh-|ecdsa-)' > "/home/$DEPLOY_USER/.ssh/authorized_keys"

    if [ ! -s "/home/$DEPLOY_USER/.ssh/authorized_keys" ]; then
      warn "Kalit ajratib olinmadi — $DEPLOY_USER uchun qo'lda qo'shing!"
    fi
    chown -R "$DEPLOY_USER:$DEPLOY_USER" "/home/$DEPLOY_USER/.ssh"
    chmod 700 "/home/$DEPLOY_USER/.ssh"
    chmod 600 "/home/$DEPLOY_USER/.ssh/authorized_keys"
  else
    warn "Hech qaysi authorized_keys topilmadi — SSH kalitni qo'lda qo'shing!"
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
RAM_MB="$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo)"

# Kichik serverda swappiness PAST bo'lmasligi kerak. 512 MB'da bo'sh turgan
# jarayonlar (celery, beat) diskka tushishi SHART, aks holda OOM killer
# Postgres'ni o'ldiradi. Katta serverda esa swap sekinlikka olib keladi.
if [ "$RAM_MB" -lt 1500 ]; then
  SWAPPINESS=60
  SWAP_SIZE=2G
else
  SWAPPINESS=10
  SWAP_SIZE=2G
fi

if ! swapon --show | grep -q .; then
  log "${SWAP_SIZE} swap yaratilmoqda (RAM: ${RAM_MB} MB)"
  fallocate -l "$SWAP_SIZE" /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
  chmod 600 /swapfile
  mkswap /swapfile >/dev/null
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi
sysctl -w vm.swappiness="$SWAPPINESS" >/dev/null
echo "vm.swappiness=$SWAPPINESS" > /etc/sysctl.d/99-swappiness.conf

if [ "$RAM_MB" -lt 1500 ]; then
  warn "RAM ${RAM_MB} MB — .env faylda LOWMEM=1 QILISHNI UNUTMANG!"
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
  1. Chiqing va QAYTA kiring (docker guruhi faqat yangi sessiyada kuchga kiradi):
       exit
       ssh $DEPLOY_USER@<SERVER_IP>
       docker ps        # sudo'siz ishlashi kerak

  2. Private repo uchun deploy key yarating va GitHub'ga qo'shing:
       ssh-keygen -t ed25519 -f ~/.ssh/github_deploy -N "" -C "alkagol-server"
       cat ~/.ssh/github_deploy.pub
       # GitHub -> repo -> Settings -> Deploy keys -> Add (write ruxsati SHART EMAS)
       printf 'Host github.com\n  IdentityFile ~/.ssh/github_deploy\n  IdentitiesOnly yes\n' >> ~/.ssh/config

  3. Reponi kloning qiling (SSH orqali, HTTPS emas):
       git clone git@github.com:<OWNER>/<REPO>.git $APP_DIR
       cd $APP_DIR

  4. .env tayyorlang:
       cp .env.example .env
       python3 -c "import secrets; print(secrets.token_urlsafe(64))"   # SECRET_KEY
       nano .env
       # To'ldirish SHART: SECRET_KEY, DOMAIN, ACME_EMAIL, POSTGRES_PASSWORD,
       #   ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS, IMAGE_OWNER (KICHIK harflarda!)
       # RAM 1 GB yoki kamroq bo'lsa: LOWMEM=1
       chmod 600 .env

  5. GHCR'ga login (private repo bo'lsa):
       # GitHub -> Settings -> Developer settings -> Tokens (classic) -> read:packages
       echo <GITHUB_PAT> | docker login ghcr.io -u <USERNAME> --password-stdin

  6. Ishga tushiring:
       ./scripts/deploy.sh latest

  7. Domen A-record serverga qarab turgach:
       ./scripts/init-letsencrypt.sh
EOF
