# =============================================================================
#  ALKAGOL — qulay buyruqlar.  `make` yoki `make help` -> ro'yxat
# =============================================================================
.DEFAULT_GOAL := help
SHELL := /bin/bash

DC      := docker compose
DC_PROD := docker compose -f docker-compose.prod.yml

.PHONY: help
help: ## Buyruqlar ro'yxati
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ----------------------------------------------------------------- Setup
.PHONY: init
init: ## Birinchi sozlash: .env fayllarni yaratadi
	@[ -f .env ] || (cp .env.example .env && echo "✓ .env yaratildi — SECRET_KEY va parollarni to'ldiring")
	@[ -f backend/.env ] || (cp backend/.env.example backend/.env && echo "✓ backend/.env yaratildi")
	@[ -f frontend/.env.local ] || (cp frontend/.env.example frontend/.env.local && echo "✓ frontend/.env.local yaratildi")

.PHONY: secret
secret: ## Yangi Django SECRET_KEY generatsiya qiladi
	@# token_urlsafe: faqat [A-Za-z0-9_-]. `$$`, `$${`, `$$(` kabi belgilar
	@# .env ichida docker compose interpolatsiyasini buzadi, shuning uchun
	@# maxsus belgilardan butunlay voz kechamiz.
	@python3 -c "import secrets; print(secrets.token_urlsafe(64))"

# ------------------------------------------------------------- Lokal stack
.PHONY: up
up: ## Lokal stack'ni ko'taradi (build bilan)
	$(DC) up --build -d
	@echo "→ http://localhost   |  Swagger: http://localhost/api/docs/"

.PHONY: down
down: ## Lokal stack'ni to'xtatadi
	$(DC) down

.PHONY: clean
clean: ## Stack + volume'larni butunlay o'chiradi (MA'LUMOT YO'QOLADI)
	$(DC) down -v --remove-orphans

.PHONY: logs
logs: ## Loglarni kuzatadi
	$(DC) logs -f --tail=100

.PHONY: ps
ps: ## Konteynerlar holati
	$(DC) ps

.PHONY: restart
restart: ## Stack'ni qayta ishga tushiradi
	$(DC) restart

# ------------------------------------------------------------------ Django
.PHONY: migrate
migrate: ## Migratsiyalarni bajaradi
	$(DC) exec backend python manage.py migrate

.PHONY: makemigrations
makemigrations: ## Yangi migratsiya fayllarini yaratadi
	$(DC) exec backend python manage.py makemigrations

.PHONY: seed
seed: ## Demo ma'lumotlarni yuklaydi
	$(DC) exec backend python manage.py seed_data

.PHONY: superuser
superuser: ## Superuser yaratadi
	$(DC) exec backend python manage.py createsuperuser

.PHONY: shell
shell: ## Django shell
	$(DC) exec backend python manage.py shell

.PHONY: bash
bash: ## Backend konteyneriga kiradi
	$(DC) exec backend bash

.PHONY: check
check: ## Django deploy tekshiruvi
	$(DC) exec backend python manage.py check --deploy

# -------------------------------------------------------------------- Test
.PHONY: test
test: ## Backend testlari
	$(DC) exec backend python manage.py test

.PHONY: lint
lint: ## Frontend lint
	cd frontend && npm run lint

.PHONY: build-fe
build-fe: ## Frontend'ni lokal build qiladi
	cd frontend && npm ci && npm run build

# -------------------------------------------------------------- Production
.PHONY: prod-up
prod-up: ## Prod stack (serverda)
	$(DC_PROD) up -d

.PHONY: prod-down
prod-down: ## Prod stack'ni to'xtatadi
	$(DC_PROD) down

.PHONY: prod-logs
prod-logs: ## Prod loglar
	$(DC_PROD) logs -f --tail=100

.PHONY: deploy
deploy: ## Prod deploy (image pull + restart + healthcheck)
	./scripts/deploy.sh $(TAG)

.PHONY: ssl
ssl: ## Let's Encrypt sertifikatini birinchi marta oladi
	./scripts/init-letsencrypt.sh

.PHONY: backup
backup: ## PostgreSQL backup
	./scripts/backup.sh
