# Alkagol — Deploy qo'llanmasi

Nol holatdan HTTPS'da ishlaydigan, CI/CD bilan avtomatlashtirilgan tizimgacha.
Ketma-ketlik: **lokal tekshiruv → GitHub → DigitalOcean droplet → domen → HTTPS → CI/CD**.

Har bir bosqichni tugatmasdan keyingisiga o'tmang — keyingi bosqich oldingisining
natijasiga tayanadi.

---

## 0. Arxitektura

Bitta Ubuntu droplet ichida Docker Compose orqali 7 ta konteyner ishlaydi:

```
                        Internet
                           │
                     :80 / :443
                           │
                    ┌──────▼──────┐
                    │    nginx    │  TLS tugatish, gzip, rate limit
                    └──┬───────┬──┘
             /api/, /admin/    │  /  va  /_next/static/
                       │       │
              ┌────────▼──┐ ┌──▼────────┐
              │  backend  │ │ frontend  │
              │ Gunicorn  │ │ Next.js   │
              │ Django 5  │ │ standalone│
              └──┬─────┬──┘ └───────────┘
                 │     │
        ┌────────▼─┐ ┌─▼──────┐   ┌──────────────┐  ┌────────────┐
        │ Postgres │ │ Redis  │◄──┤ celery_worker│  │ celery_beat│
        │    16    │ │   7    │   └──────────────┘  └────────────┘
        └──────────┘ └────────┘
```

Muhim qarorlar va sabablari:

Frontend brauzerga `/api` (nisbiy yo'l) bilan chiqadi, ya'ni so'rov o'zi turgan
domenga ketadi. Shu sababli **CORS umuman kerak emas** va preflight so'rovlar
yo'qoladi. Postgres va Redis portlari tashqariga **umuman ochilmaydi** — faqat
Docker ichki tarmog'ida ko'rinadi. Image'lar serverda emas, **GitHub Actions'da
build qilinadi** va GHCR'ga push qilinadi; droplet faqat tayyor image'ni tortadi.
2 GB RAM'li dropletda `next build` xotira yetishmasligidan o'lishi mumkin, shuning
uchun bu ataylab shunday.

---

## 1. Lokal tekshiruv (o'z kompyuteringizda)

Deploy qilishdan oldin hamma narsa lokalda ishlashiga ishonch hosil qiling.

### 1.1. Sozlash

```bash
cd ~/Desktop/Projects/alkagol

# .env fayllarni namunadan yaratadi
make init

# Django uchun kuchli kalit generatsiya qiladi
make secret
```

Chiqqan kalitni `.env` ichidagi `SECRET_KEY=` ga qo'ying va `POSTGRES_PASSWORD`
ni ham o'zgartiring. Lokal uchun `.env` da quyidagilar yetarli:

```ini
DOMAIN=localhost
ALLOWED_HOSTS=localhost,127.0.0.1,backend
CSRF_TRUSTED_ORIGINS=http://localhost
SESSION_COOKIE_SECURE=False      # lokalda HTTPS yo'q
CSRF_COOKIE_SECURE=False
SECURE_HSTS_SECONDS=0
```

> `SESSION_COOKIE_SECURE=True` ni lokalda qoldirsangiz login ishlamaydi —
> brauzer HTTP orqali secure cookie'ni saqlamaydi.

### 1.2. Ishga tushirish

```bash
make up          # docker compose up --build -d
make logs        # kuzatib turing
```

Backend konteyneri o'zi Postgres'ni kutadi, `migrate` va `collectstatic` qiladi.
Tayyor bo'lgach:

- Ilova: <http://localhost>
- Swagger: <http://localhost/api/docs/>
- Admin: <http://localhost/admin/>

### 1.3. Ma'lumot va foydalanuvchi

```bash
make superuser   # admin yaratish
make seed        # demo ma'lumotlar (seed_data buyrug'i)
```

### 1.4. Tekshiruvlar

```bash
make check       # manage.py check --deploy — xavfsizlik ogohlantirishlari
make test        # backend testlari
make lint        # frontend ESLint
cd frontend && npx tsc --noEmit    # TypeScript tiplar
```

`make check` da `SECURE_SSL_REDIRECT` va `SECURE_HSTS_SECONDS` haqidagi
ogohlantirishlar **lokalda normal** — prod `.env` da ular yoqiladi.

### 1.5. To'xtatish

```bash
make down        # konteynerlar to'xtaydi, ma'lumot saqlanadi
make clean       # volume'lar ham o'chadi — MA'LUMOT YO'QOLADI
```

---

## 2. GitHub'ga yuklash (private monorepo)

### 2.1. Oxirgi xavfsizlik tekshiruvi

Commit qilishdan oldin hech qanday sir repo'ga tushmayotganini tasdiqlang:

```bash
git status --short
git ls-files | grep -E '\.env$|db\.sqlite3|node_modules|venv/' && echo "!!! TO'XTANG" || echo "toza"
```

Natija `toza` bo'lishi shart. `.env.example` fayllar bo'lishi kerak — ular
namuna, ichida haqiqiy parol yo'q.

### 2.2. Commit

```bash
git add -A
git commit -m "chore: production deploy konfiguratsiyasi"
```

### 2.3. GitHub'da repo yaratish

Brauzerda <https://github.com/new> → nom `alkagol` → **Private** → README/gitignore/license
qo'shmang (bizda allaqachon bor) → Create.

Yoki `gh` CLI bilan:

```bash
gh repo create alkagol --private --source=. --remote=origin --push
```

Qo'lda:

```bash
git remote add origin git@github.com:<USERNAME>/alkagol.git
git push -u origin main
```

> SSH kalitingiz GitHub'ga ulanmagan bo'lsa:
> `ssh-keygen -t ed25519 -C "email@example.com"` → `cat ~/.ssh/id_ed25519.pub`
> → GitHub → Settings → SSH and GPG keys → New SSH key.

### 2.4. GHCR paketlari

Image'lar `ghcr.io/<USERNAME>/alkagol-backend` va `-frontend` sifatida saqlanadi.
Birinchi push'dan keyin GitHub avtomatik yaratadi — oldindan hech narsa qilish
kerak emas.

---

## 3. DigitalOcean droplet

### 3.1. Droplet yaratish

DigitalOcean panelida: **Create → Droplets**

| Parametr | Tanlov | Izoh |
|---|---|---|
| Image | Ubuntu 24.04 LTS x64 | |
| Plan | Basic → Regular → **2 GB / 2 vCPU / 60 GB** | $18/oy. 1 GB ham ishlaydi, lekin siqiq |
| Datacenter | Frankfurt yoki Amsterdam | O'zbekistonga eng past kechikish |
| Authentication | **SSH Key** | Parol emas — xavfsizroq |
| Hostname | `alkagol-prod` | |

Qo'shimcha: **Enable backups** ($3.6/oy) — tavsiya qilinadi.

### 3.2. Serverni sozlash

Droplet IP'sini oling va root sifatida kiring:

```bash
ssh root@<DROPLET_IP>
```

Sozlash skriptini serverga ko'chiring. Repo **private** bo'lgani uchun uni
`curl` bilan yuklab bo'lmaydi — lokal kompyuteringizdan `scp` qiling:

```bash
# LOKAL terminalda:
scp scripts/server-setup.sh root@<DROPLET_IP>:/root/
```

Keyin serverda ishga tushiring — u Docker, `deploy` foydalanuvchisi, UFW,
fail2ban, 2 GB swap va cron vazifalarini o'rnatadi:

```bash
bash /root/server-setup.sh
```

Skript nima qiladi: tizimni yangilaydi, Docker Engine + Compose plugin o'rnatadi,
`deploy` nomli sudo foydalanuvchi yaratib unga SSH kalitingizni ko'chiradi, UFW'da
faqat 22/80/443 portlarni ochadi, fail2ban'ni yoqadi, 2 GB swap fayl yaratadi
(kichik dropletda OOM'dan saqlaydi), `unattended-upgrades` ni yoqadi va
`/opt/alkagol` papkasini tayyorlaydi.

Tugagach `deploy` foydalanuvchisi bilan kiring:

```bash
exit
ssh deploy@<DROPLET_IP>
```

### 3.3. Serverda deploy kaliti (private repo uchun)

Server private repo'ni klon qilishi uchun unga o'qish huquqi kerak.
**Deploy key** eng xavfsiz variant — u faqat shu bitta repo'ga tegishli.

Serverda:

```bash
ssh-keygen -t ed25519 -C "alkagol-droplet" -f ~/.ssh/id_ed25519 -N ""
cat ~/.ssh/id_ed25519.pub
```

Chiqqan matnni nusxa oling → GitHub → repo → **Settings → Deploy keys →
Add deploy key** → Title: `droplet`, Key: yopishtiring, **Allow write access
BELGILAMANG** → Add key.

Tekshirish:

```bash
ssh -T git@github.com     # "Hi <USERNAME>/alkagol! You've successfully authenticated"
```

### 3.4. Repo'ni klon qilish

```bash
sudo chown -R deploy:deploy /opt/alkagol
git clone git@github.com:<USERNAME>/alkagol.git /opt/alkagol
cd /opt/alkagol
```

### 3.5. Prod `.env`

```bash
cp .env.example .env
nano .env
```

To'ldirish shart bo'lgan qatorlar:

```ini
DOMAIN=alkagol.uz                      # domeningiz (hozircha IP ham bo'ladi)
ACME_EMAIL=siz@example.com

SECRET_KEY=<make secret natijasi>
DEBUG=False
ALLOWED_HOSTS=alkagol.uz,www.alkagol.uz,backend,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://alkagol.uz,https://www.alkagol.uz
CORS_ALLOWED_ORIGINS=https://alkagol.uz

POSTGRES_PASSWORD=<kuchli parol>

ADMIN_URL=<oddiy "admin" emas — masalan boshqaruv-7f3a>
ENABLE_API_DOCS=False                  # prod'da Swagger yopiq

IMAGE_OWNER=<github-username>          # kichik harflar bilan!
IMAGE_TAG=latest

GUNICORN_WORKERS=5                     # 2 vCPU uchun (2*2)+1
```

`SECRET_KEY` ni serverda generatsiya qilish:

```bash
python3 -c "import secrets;print(secrets.token_urlsafe(64))"
```

> `token_urlsafe` faqat `A-Za-z0-9_-` beradi. Maxsus belgili kalit
> (`$`, `${`, `$(`) `.env` da docker compose interpolatsiyasini buzadi —
> SECRET_KEY jimgina o'zgarib ketadi yoki compose umuman ishga tushmaydi.

Faylni himoyalang:

```bash
chmod 600 .env
```

> `IMAGE_OWNER` **kichik harflarda** bo'lishi shart — GHCR katta harfli
> nomlarni qabul qilmaydi.

### 3.6. GHCR'ga login

Server private image'larni tortishi uchun token kerak.

GitHub → Settings → Developer settings → **Personal access tokens (classic)** →
Generate new token → scope: **`read:packages`** → yarating va nusxa oling.

Serverda:

```bash
echo '<TOKEN>' | docker login ghcr.io -u <USERNAME> --password-stdin
```

### 3.7. Birinchi ishga tushirish

Prod compose faqat tayyor image'lar bilan ishlaydi (`build:` bloklari yo'q —
2 GB dropletda `next build` xotira yetishmasligidan o'ladi). Shuning uchun avval
GitHub Actions image'larni yig'ib berishi kerak.

`main` ga push qilingandan keyin Actions tab'ida `Deploy` workflow'ning **build**
job'i tugashini kuting (deploy job'i o'zi ham serverga ulanib deploy qiladi).
Qo'lda ishga tushirmoqchi bo'lsangiz serverda:

```bash
cd /opt/alkagol
./scripts/deploy.sh latest
```

`deploy.sh` sertifikat yo'qligini sezsa vaqtinchalik self-signed sertifikat
yaratadi — nginx'ning "sertifikat yo'q → start bo'lmaydi → sertifikat olinmaydi"
halqasini shu buzadi. Sayt bu bosqichda HTTPS ogohlantirishi bilan ochiladi;
haqiqiy sertifikatni 5-bo'limda olamiz.

Holatni tekshiring:

```bash
docker compose -f docker-compose.prod.yml ps

# Prod nginx'da 80-port faqat redirect va ACME uchun, server_name esa $DOMAIN.
# Shuning uchun Host sarlavhasi bilan HTTPS'ga uramiz (-k: self-signed):
DOMAIN=$(grep -m1 '^DOMAIN=' .env | cut -d= -f2-)
curl -fsSk -H "Host: $DOMAIN" https://127.0.0.1/api/health/    # {"status":"ok"}
```

Superuser yarating:

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

Endi <http://DROPLET_IP> da ilova ochilishi kerak (brauzer sertifikat haqida
ogohlantiradi — bu normal, 5-bo'limdan keyin yo'qoladi).

---

## 4. Domenni ulash

### 4.1. DNS yozuvlari

Domen registratoringiz panelida (yoki DigitalOcean → Networking → Domains):

| Turi | Nom | Qiymat | TTL |
|---|---|---|---|
| A | `@` | `<DROPLET_IP>` | 3600 |
| A | `www` | `<DROPLET_IP>` | 3600 |

Tarqalishini kuting (odatda 5–30 daqiqa) va tekshiring:

```bash
dig +short alkagol.uz        # DROPLET_IP chiqishi kerak
dig +short www.alkagol.uz
```

> DNS tarqalmasdan turib keyingi bosqichga o'tmang — Let's Encrypt domenni
> tekshira olmasa, ko'p urinishdan keyin sizni vaqtincha bloklaydi
> (haftasiga 5 ta muvaffaqiyatsiz urinish limiti).

### 4.2. `.env` ni yangilash

Agar `.env` da IP yozgan bo'lsangiz, endi haqiqiy domenni qo'ying:

```bash
nano /opt/alkagol/.env
# DOMAIN, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS, CORS_ALLOWED_ORIGINS
```

---

## 5. HTTPS (Let's Encrypt)

```bash
cd /opt/alkagol
./scripts/init-letsencrypt.sh
```

Skript ketma-ketligi: avval **dummy sertifikat** yaratadi (nginx sertifikatsiz
start bo'lolmaydi — "tovuq va tuxum" muammosi), nginx'ni ko'taradi, dummy'ni
o'chirib Certbot orqali **haqiqiy sertifikat** oladi (webroot usuli, `/.well-known/`
orqali), keyin nginx'ni reload qiladi.

Tekshiruv:

```bash
curl -I https://alkagol.uz              # HTTP/2 200
curl -I http://alkagol.uz               # 301 -> https
curl -fsS https://alkagol.uz/api/health/
```

Sertifikat sifatini <https://www.ssllabs.com/ssltest/> da tekshirsangiz **A**
yoki **A+** chiqishi kerak.

### Avtomatik yangilanish

`server-setup.sh` cron yozuvini qo'shgan (`scripts/ssl-renew.sh`, haftasiga bir
marta) va `docker-compose.prod.yml` ichida `certbot` konteyneri 12 soatda bir
`renew` qiladi. Qo'lda tekshirish:

```bash
docker compose -f docker-compose.prod.yml run --rm \
  --entrypoint certbot certbot renew --dry-run
```

> `--entrypoint certbot` **majburiy**: servisning o'z entrypoint'i cheksiz sikl,
> uni almashtirmasangiz buyruq hech qachon tugamaydi.

---

## 6. CI/CD

### 6.1. Nima qachon ishlaydi

| Workflow | Trigger | Nima qiladi |
|---|---|---|
| `ci.yml` | har PR va `main` push | ruff, `manage.py check`, migratsiya dreyfi, testlar, `tsc --noEmit`, ESLint, `next build`, Docker build |
| `deploy.yml` | `main` push, `v*` tag, qo'lda | image build → GHCR push → SSH orqali serverda `deploy.sh` → tashqi smoke test |

### 6.2. GitHub secrets

Repo → **Settings → Secrets and variables → Actions → Secrets → New repository secret**:

| Nom | Qiymat |
|---|---|
| `DO_HOST` | droplet IP manzili |
| `DO_USER` | `deploy` |
| `DO_SSH_KEY` | **private** kalit (butun matn, `-----BEGIN` dan `-----END` gacha) |
| `DO_SSH_PORT` | `22` (SSH portini o'zgartirgan bo'lsangiz — o'shani) |

`GITHUB_TOKEN` avtomatik beriladi — qo'lda qo'shmaysiz.

CI uchun alohida kalit juftligi yarating (shaxsiy kalitingizni bermang):

```bash
# LOKAL kompyuterda:
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/alkagol_ci -N ""

# Public kalitni serverga qo'shing:
ssh-copy-id -i ~/.ssh/alkagol_ci.pub deploy@<DROPLET_IP>

# Private kalitni GitHub secret DO_SSH_KEY ga yopishtiring:
cat ~/.ssh/alkagol_ci
```

### 6.3. GitHub variables

**Variables** tab'ida (Secrets emas):

| Nom | Qiymat |
|---|---|
| `DOMAIN` | `alkagol.uz` |

Bu smoke test va deploy xulosasi uchun ishlatiladi.

### 6.4. Package huquqlari

Agar deploy `denied` xatosi bersa: GitHub → repo → **Settings → Actions →
General → Workflow permissions** → **Read and write permissions** ni yoqing.

### 6.5. Birinchi avtomatik deploy

```bash
git commit --allow-empty -m "ci: birinchi avtomatik deploy"
git push
```

Actions tab'ida kuzating. Muvaffaqiyatli bo'lsa oxirida "DEPLOY MUVAFFAQIYATLI"
va domen havolasi chiqadi.

### 6.6. Versiyalangan reliz

```bash
git tag -a v1.0.0 -m "Birinchi reliz"
git push origin v1.0.0
```

Image `ghcr.io/<user>/alkagol-backend:v1.0.0` sifatida saqlanadi va shu tag
deploy qilinadi. Kerak bo'lsa eski versiyaga qaytish oson:

```bash
# Serverda:
./scripts/deploy.sh v1.0.0
```

---

## 7. Kundalik ishlar

### Loglar

```bash
cd /opt/alkagol
docker compose -f docker-compose.prod.yml logs -f --tail=100
docker compose -f docker-compose.prod.yml logs -f backend
```

### Backup

Nightly cron `scripts/backup.sh` ni ishga tushiradi (`pg_dump | gzip`,
`/opt/alkagol/backups/`, 14 kun saqlanadi). Qo'lda:

```bash
./scripts/backup.sh
ls -lh backups/
```

Backupni tashqariga ko'chiring — droplet o'lsa backup ham o'ladi:

```bash
# LOKAL kompyuterda:
rsync -avz deploy@<IP>:/opt/alkagol/backups/ ~/alkagol-backups/
```

### Tiklash

```bash
gunzip -c backups/alkagol_2026-09-02.sql.gz | \
  docker compose -f docker-compose.prod.yml exec -T db \
  psql -U alkagol_user -d alkagol_db
```

### Migratsiya

Odatda avtomatik (backend entrypoint `RUN_MIGRATIONS=true`). Qo'lda:

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate
```

### Resurslarni kuzatish

```bash
docker stats --no-stream
df -h
free -h
```

---

## 8. Muammolarni hal qilish

**502 Bad Gateway** — backend ko'tarilmagan.
`docker compose -f docker-compose.prod.yml logs backend` da sabab ko'rinadi.
Ko'p uchraydigani: `.env` da `POSTGRES_PASSWORD` noto'g'ri yoki `SECRET_KEY` bo'sh.

**DisallowedHost xatosi** — `ALLOWED_HOSTS` ga domen qo'shilmagan.
`.env` ni tuzating va `docker compose -f docker-compose.prod.yml restart backend`.

**CSRF verification failed (admin panelda)** — `CSRF_TRUSTED_ORIGINS` da
`https://` prefiksi yo'q. Sxema bilan yozilishi shart.

**Static fayllar 404** — `collectstatic` ishlamagan.
`docker compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput`.

**Let's Encrypt "too many failed authorizations"** — DNS tayyor bo'lmasdan
urinilgan. Bir soat kuting, DNS'ni `dig` bilan tasdiqlang, keyin qayta urining.

**Deploy `denied: permission_denied` beradi** — serverda `docker login ghcr.io`
qilinmagan yoki token muddati tugagan (3.6-bo'limga qarang).

**Konteyner OOM bilan o'ladi** — swap yo'q yoki `GUNICORN_WORKERS` juda katta.
`free -h` bilan tekshiring, `swapon --show` bo'sh bo'lsa `server-setup.sh` ning
swap qismini qayta ishga tushiring.

**Deploy muvaffaqiyatsiz bo'ldi va sayt ishlamayapti** — `deploy.sh` avtomatik
rollback qiladi. Agar qilmagan bo'lsa qo'lda:

```bash
sed -i 's|^IMAGE_TAG=.*|IMAGE_TAG=<oldingi-tag>|' .env
docker compose -f docker-compose.prod.yml up -d --no-build
```

---

## 9. Deploydan keyingi xavfsizlik ro'yxati

- [ ] `.env` da `DEBUG=False`
- [ ] `SECRET_KEY` — 50+ belgi, hech qayerda takrorlanmagan
- [ ] `ADMIN_URL` — `admin` emas
- [ ] `ENABLE_API_DOCS=False`
- [ ] `chmod 600 /opt/alkagol/.env`
- [ ] `sudo ufw status` → faqat 22, 80, 443
- [ ] `sudo fail2ban-client status sshd` → faol
- [ ] SSH'da parol bilan kirish o'chirilgan (`PasswordAuthentication no`)
- [ ] `manage.py check --deploy` → 0 ta ERROR
- [ ] SSL Labs → A yoki A+
- [ ] Backup ishlayotgani tekshirilgan va tashqariga ko'chirilgan
- [ ] DigitalOcean backups yoqilgan
- [ ] GHCR tokeni faqat `read:packages` huquqiga ega
