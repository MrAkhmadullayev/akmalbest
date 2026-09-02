# Alkagol — Deploy qo'llanmasi

Nol holatdan HTTPS'da ishlaydigan, CI/CD bilan avtomatlashtirilgan tizimgacha.
Ketma-ketlik: **lokal tekshiruv → GitHub → AWS EC2 → domen → HTTPS → CI/CD**.

Har bir bosqichni tugatmasdan keyingisiga o'tmang — keyingi bosqich oldingisining
natijasiga tayanadi.

---

## 0. Arxitektura

Bitta Ubuntu serverda Docker Compose orqali 7 ta konteyner ishlaydi:

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
build qilinadi** va GHCR'ga push qilinadi; server faqat tayyor image'ni tortadi.
Kichik serverda `next build` xotira yetishmasligidan o'lishi mumkin, shuning
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

## 3. AWS EC2 server

### 3.0. Lokal SSH kaliti

Kalit yo'q bo'lsa avval yarating (passphrase **bo'sh** bo'lishi shart — CI/CD
avtomatik ulanadi, parol so'ralsa deploy to'xtaydi):

```bash
ssh-keygen -t ed25519 -C "alkagol-deploy" -f ~/.ssh/id_ed25519 -N ""
cat ~/.ssh/id_ed25519.pub
```

### 3.1. Instance yaratish

EC2 konsolida: **Launch instance**

| Parametr | Tanlov | Izoh |
|---|---|---|
| Name | `alkagol-prod` | |
| AMI | **Ubuntu Server 24.04 LTS (64-bit x86)** | ARM/Graviton'ni TANLAMANG — pastdagi izohga qarang |
| Instance type | **t3.micro** | 1 GB RAM, Free Tier'da 12 oy bepul |
| Key pair | yangi yarating yoki mavjudini tanlang | "Import key pair" bilan yuqoridagi `.pub` ni yuklang |
| Network → Auto-assign public IP | **Enable** | |
| Security group | quyidagi jadval | |
| Storage | **30 GB gp3** | Free Tier chegarasi aynan 30 GB |

**Nega x86:** `t4g` tipidagi instance'lar ARM protsessorda ishlaydi. Bizning
Docker image'lar GitHub Actions'da `linux/amd64` uchun yig'iladi va ARM
mashinada `exec format error` beradi. Agar keyinchalik ARM'ga o'tmoqchi
bo'lsangiz ayting — CI'ni multi-arch build'ga o'tkazaman.

**Security group qoidalari** (Inbound):

| Type | Port | Source | Izoh |
|---|---|---|---|
| SSH | 22 | **My IP** | Faqat sizning IP'ingiz. Internet-provayder IP'ni o'zgartirsa yangilash kerak |
| HTTP | 80 | `0.0.0.0/0` | Let's Encrypt tekshiruvi uchun ochiq bo'lishi SHART |
| HTTPS | 443 | `0.0.0.0/0` | |

PostgreSQL (5432) va Redis (6379) uchun qoida **qo'shmang** — ular faqat
konteynerlar ichki tarmog'ida ishlaydi.

### 3.1a. Elastic IP (majburiy)

EC2'ning oddiy public IP'si instance to'xtab-ishga tushganda **o'zgaradi**.
DNS yozuvi va GitHub secret eski IP'ga qarab qolsa sayt o'chadi. Shuning uchun:

**EC2 → Elastic IPs → Allocate Elastic IP address → Actions → Associate** →
instance'ni tanlang.

Elastic IP instance'ga biriktirilgan holda bepul. Biriktirilmasdan bo'sh
turgani uchun AWS pul oladi, shuning uchun keraksiz bo'lsa **Release** qiling.

Shu IP butun qo'llanmada `<SERVER_IP>` deb yuritiladi.

### 3.2. Serverni sozlash

EC2 Ubuntu AMI'da `root` bilan to'g'ridan-to'g'ri kirib bo'lmaydi — `ubuntu`
foydalanuvchisi ishlatiladi.

```bash
# LOKAL terminalda:
cd ~/Desktop/Projects/alkagol
ssh ubuntu@<SERVER_IP> "echo ulanish OK"
scp scripts/server-setup.sh ubuntu@<SERVER_IP>:/tmp/
ssh ubuntu@<SERVER_IP> "sudo bash /tmp/server-setup.sh ubuntu"
```

Oxirgi argument `ubuntu` — ya'ni yangi foydalanuvchi yaratilmaydi, mavjud
`ubuntu` foydalanuvchisi docker guruhiga qo'shiladi. Bu EC2'da eng sodda yo'l.

Skript 3–5 daqiqada: tizimni yangilaydi, Docker Engine + Compose plugin
o'rnatadi, UFW'da faqat 22/80/443 ni ochadi (Security Group ustiga ikkinchi
himoya qatlami), fail2ban va `unattended-upgrades` ni yoqadi, RAM hajmiga
qarab 2 GB swap yaratadi, `/opt/alkagol` papkasini tayyorlaydi va kunlik
backup cron'ini qo'yadi.

Tugagach **albatta chiqib qayta kiring** — `docker` guruhiga a'zolik faqat
yangi sessiyada kuchga kiradi:

```bash
ssh ubuntu@<SERVER_IP>
docker ps        # `sudo` siz ishlashi kerak
free -h          # swap ko'rinishi kerak
```

### 3.3. Serverda deploy kaliti (private repo uchun)

Server private repo'ni klon qilishi uchun unga o'qish huquqi kerak.
**Deploy key** eng xavfsiz variant — u faqat shu bitta repo'ga tegishli va
akkauntingizning qolgan repolariga tegmaydi.

Serverda:

```bash
ssh-keygen -t ed25519 -C "alkagol-server" -f ~/.ssh/github_deploy -N ""
printf 'Host github.com\n  IdentityFile ~/.ssh/github_deploy\n  IdentitiesOnly yes\n' >> ~/.ssh/config
cat ~/.ssh/github_deploy.pub
```

Kalitni alohida faylga yozayapmiz (`id_ed25519` emas), chunki `id_ed25519`
keyinroq boshqa maqsadda kerak bo'lishi mumkin va ikkalasi aralashib ketmasin.
`~/.ssh/config` git'ga qaysi kalitni ishlatishni aytadi.

Chiqqan matnni nusxa oling → GitHub → repo → **Settings → Deploy keys →
Add deploy key** → Title: `aws-ec2`, Key: yopishtiring, **Allow write access
BELGILAMANG** → Add key.

Tekshirish:

```bash
ssh -T git@github.com
# "Hi MrAkhmadullayev/akmalbest! You've successfully authenticated..."
```

### 3.4. Repo'ni klon qilish

```bash
sudo chown -R ubuntu:ubuntu /opt/alkagol
git clone git@github.com:MrAkhmadullayev/akmalbest.git /opt/alkagol
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

IMAGE_OWNER=mrakhmadullayev            # kichik harflar bilan!
IMAGE_TAG=latest

LOWMEM=1                               # t3.micro (1 GB) uchun — pastga qarang
GUNICORN_WORKERS=1                     # LOWMEM=1 bo'lsa baribir 1 ga majburlanadi
```

**`LOWMEM` haqida.** RAM 1 GB yoki undan kam bo'lsa `LOWMEM=1` qiling. Shunda
barcha skriptlar `docker-compose.lowmem.yml` ni avtomatik qo'shadi va
konfiguratsiya siqiladi: Postgres `shared_buffers` 128 MB dan 16 MB ga tushadi,
Redis snapshot'ni o'chiradi (fork paytida xotira ikkilanmasin), Gunicorn 3 ta
worker o'rniga 1 worker + 8 thread ishlatadi, `celery_beat` alohida konteyner
sifatida ishga tushmay worker ichiga ko'chadi (~100 MB tejaydi), certbot demoni
o'chadi va sertifikat yangilash faqat haftalik cron orqali bo'ladi.

Keyinchalik instance tipini `t3.small` ga (2 GB) oshirsangiz `LOWMEM=0` qilib
`./scripts/deploy.sh latest` ni qayta ishga tushiring — hech narsani
o'chirish yoki qayta yozish shart emas.

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
t3.micro'da `next build` xotira yetishmasligidan o'ladi). Shuning uchun avval
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

Endi <http://SERVER_IP> da ilova ochilishi kerak (brauzer sertifikat haqida
ogohlantiradi — bu normal, 5-bo'limdan keyin yo'qoladi).

---

## 4. Domenni ulash

### 4.1. DNS yozuvlari

Domen registratoringiz panelida (yoki AWS Route 53 → Hosted zones):

| Turi | Nom | Qiymat | TTL |
|---|---|---|---|
| A | `@` | `<SERVER_IP>` | 3600 |
| A | `www` | `<SERVER_IP>` | 3600 |

Tarqalishini kuting (odatda 5–30 daqiqa) va tekshiring:

```bash
dig +short alkagol.uz        # SERVER_IP chiqishi kerak
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
| `SSH_HOST` | serverning **Elastic IP** manzili |
| `SSH_USER` | `ubuntu` (EC2 Ubuntu AMI'da) |
| `SSH_KEY` | **private** kalit (butun matn, `-----BEGIN` dan `-----END` gacha) |
| `SSH_PORT` | `22` (SSH portini o'zgartirgan bo'lsangiz — o'shani) |

> Security group'da 22-portni "My IP" ga cheklagan bo'lsangiz, GitHub Actions
> runner'i boshqa IP'dan keladi va ulanolmaydi. Ikki yo'l bor: 22-portni
> `0.0.0.0/0` ga ochish (fail2ban va parolsiz kalit himoya qiladi), yoki
> AWS'ning GitHub Actions IP diapazonlarini qo'shish. Sodda yechim —
> birinchisi.

`GITHUB_TOKEN` avtomatik beriladi — qo'lda qo'shmaysiz.

CI uchun alohida kalit juftligi yarating (shaxsiy kalitingizni bermang):

```bash
# LOKAL kompyuterda:
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/alkagol_ci -N ""

# Public kalitni serverga qo'shing:
ssh-copy-id -i ~/.ssh/alkagol_ci.pub ubuntu@<SERVER_IP>

# Private kalitni GitHub secret SSH_KEY ga yopishtiring (butun matn):
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

Backupni tashqariga ko'chiring — server o'lsa backup ham o'ladi:

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
- [ ] EC2 snapshot yoki AWS Backup yoqilgan
- [ ] GHCR tokeni faqat `read:packages` huquqiga ega
