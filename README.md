# Alkagol — CRM + POS + Ombor + Nasiya boshqaruv tizimi

Alkogol mahsulotlari do'koni uchun to'liq full-stack tizim: kassa (POS), ombor,
mijozlar, nasiya hisob-kitobi va hisobotlar.

**Stack:** Django 5.1 + DRF + Celery · Next.js 16 + React 19 + TypeScript ·
PostgreSQL 16 · Redis 7 · Nginx · Docker

---

## Modullar

| Modul | Tavsif |
|---|---|
| Accounts & RBAC | Custom user model, rollar: `SUPER_ADMIN`, `ADMIN`, `CASHIER`, `WAREHOUSE_MANAGER` |
| Mahsulotlar | Shtrix-kod bo'yicha unikal indeks, kategoriya, brend, narx va zaxira darajalari |
| Ombor | `select_for_update` bilan atomik o'zgarishlar — parallel sotuvda qoldiq buzilmaydi |
| CRM va nasiya | Mijoz profillari, qarz tarixi, muddat bo'yicha ogohlantirish |
| POS kassa | Skaner orqali qo'shish, chegirma, qaytim hisoblagich, chek chop etish |
| Hisobotlar | Tushum, foyda, tannarx, kam qolgan/tugagan tovar, muddati o'tgan qarzlar |

---

## Tez boshlash

Talab: Docker Desktop (yoki Docker Engine + Compose plugin).

```bash
make init          # .env fayllarni namunadan yaratadi
make secret        # SECRET_KEY generatsiya qiladi -> .env ga qo'ying
make up            # butun stack'ni ko'taradi
make superuser     # admin foydalanuvchi
make seed          # demo ma'lumotlar
```

Ochiladi:

- Ilova — <http://localhost>
- API — <http://localhost/api/>
- Swagger — <http://localhost/api/docs/>
- Admin — <http://localhost/admin/>

> Lokalda `.env` ichida `SESSION_COOKIE_SECURE=False` va `CSRF_COOKIE_SECURE=False`
> bo'lishi kerak, aks holda HTTP orqali login ishlamaydi.

Barcha buyruqlar ro'yxati: `make help`

---

## Docker'siz ishlash (backend'ni tahrirlash uchun)

Postgres va Redis'ni Docker'da qoldirib, Django'ni lokal ishga tushirish qulay:

```bash
docker compose up -d db redis

python3.13 -m venv venv
source venv/bin/activate
pip install -r backend/requirements-dev.txt

cp backend/.env.example backend/.env
cd backend
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

Celery (alohida terminallarda):

```bash
cd backend
celery -A config worker -l info
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

Frontend:

```bash
cd frontend
npm install
cp .env.example .env.local     # NEXT_PUBLIC_API_URL=http://localhost:8000/api
npm run dev                    # http://localhost:3000
```

---

## Loyiha tuzilishi

```
alkagol/
├── backend/                 Django loyihasi
│   ├── config/              settings, urls, celery, health endpoints
│   ├── apps/                accounts, products, inventory, sales,
│   │                        customers, debts, suppliers, expenses,
│   │                        notifications, reports, core
│   ├── Dockerfile           multi-stage, non-root, healthcheck
│   ├── entrypoint.sh        DB kutish -> migrate -> collectstatic
│   ├── requirements.txt     faqat prod
│   └── requirements-dev.txt prod + pytest, ruff, django-extensions
├── frontend/                Next.js App Router (standalone build)
├── nginx/
│   ├── dev.conf             lokal (HTTP)
│   └── templates/           prod (TLS, HSTS, rate limit, envsubst)
├── scripts/
│   ├── server-setup.sh      droplet bootstrap: Docker, UFW, swap, cron
│   ├── init-letsencrypt.sh  birinchi sertifikat
│   ├── deploy.sh            pull -> restart -> health -> rollback
│   ├── backup.sh            pg_dump + 14 kunlik saqlash
│   └── ssl-renew.sh         sertifikat yangilash
├── .github/workflows/       ci.yml (test) + deploy.yml (GHCR -> SSH)
├── docker-compose.yml       lokal
├── docker-compose.prod.yml  server (GHCR image'lari, TLS, limitlar)
├── .env.example             yagona konfiguratsiya manbai
└── DEPLOYMENT.md            to'liq deploy qo'llanmasi
```

---

## Tekshiruvlar

```bash
make check                       # manage.py check --deploy
make test                        # backend testlari
make lint                        # frontend ESLint
cd frontend && npx tsc --noEmit  # TypeScript
```

Har bir PR'da CI shu tekshiruvlarni + `next build` + Docker build'ni bajaradi.

---

## Konfiguratsiya

Barcha sozlamalar `.env` orqali beriladi — kodda hech qanday sir yo'q.
To'liq ro'yxat va izohlar: [`.env.example`](.env.example).

Eng muhimlari:

| O'zgaruvchi | Izoh |
|---|---|
| `SECRET_KEY` | Django kaliti — har muhitda alohida |
| `DEBUG` | Prod'da doim `False` |
| `ALLOWED_HOSTS` | Sxemasiz, vergul bilan. `backend` ham kerak (nginx ichki so'rovlari) |
| `CSRF_TRUSTED_ORIGINS` | `https://` bilan — Django 4+ talabi |
| `ADMIN_URL` | Admin panel yo'li — `admin` qoldirmang |
| `ENABLE_API_DOCS` | Prod'da `False` (Swagger yopiladi) |
| `NEXT_PUBLIC_API_URL` | Prod'da `/api` — nisbiy yo'l, CORS kerak emas |
| `IMAGE_OWNER` | GHCR uchun GitHub username (kichik harflarda) |

---

## Deploy

To'liq qo'llanma: **[DEPLOYMENT.md](DEPLOYMENT.md)**

Qisqacha: GitHub (private) → DigitalOcean droplet + Docker Compose → domen →
Let's Encrypt → GitHub Actions orqali avtomatik deploy.

`main` ga push qilinganda CI test qiladi, image'larni GHCR'ga push qiladi va
SSH orqali serverda `deploy.sh` ni ishga tushiradi. Health tekshiruvi
muvaffaqiyatsiz bo'lsa oldingi versiyaga avtomatik qaytadi.
