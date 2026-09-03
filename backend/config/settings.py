"""
Django settings for Alkagol Store Management System.
"""
import os
import sys
from datetime import timedelta
from pathlib import Path

from decouple import Csv, config

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Security
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# Docker healthcheck `curl http://127.0.0.1:8000/api/health/` yuboradi, nginx esa
# upstream'ga `Host: backend` bilan boradi. Bu uchtasi ALLOWED_HOSTS'da bo'lmasa
# Django 400 DisallowedHost qaytaradi -> konteyner "unhealthy" -> celery
# servislari startga tushmaydi -> deploy rollback qiladi. Foydalanuvchi .env da
# faqat domenini yozib qo'yishi juda ehtimolli, shuning uchun majburan qo'shamiz.
for _internal_host in ('127.0.0.1', 'localhost', 'backend'):
    if _internal_host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_internal_host)

# Trusted origins for CSRF (Django >= 4 talab qiladi: sxema bilan to'liq origin)
# Masalan: https://alkagol.uz,https://www.alkagol.uz
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())

# Security Headers & Hardening
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'

# Nginx/Traefik orqasida turganda HTTPS'ni to'g'ri aniqlash uchun
USE_X_FORWARDED_HOST = config('USE_X_FORWARDED_HOST', default=False, cast=bool)
if config('TRUST_PROXY_SSL_HEADER', default=False, cast=bool):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Production Security (Enable via env vars in prod)
if not DEBUG:
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=False, cast=bool)
    SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=False, cast=bool)
    CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=False, cast=bool)
    CSRF_COOKIE_HTTPONLY = config('CSRF_COOKIE_HTTPONLY', default=True, cast=bool)
    SESSION_COOKIE_HTTPONLY = True
    SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=0, cast=int)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = config('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=False, cast=bool)
    SECURE_HSTS_PRELOAD = config('SECURE_HSTS_PRELOAD', default=False, cast=bool)

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    # Logout/rotation'da refresh tokenni haqiqiy bekor qilish uchun SHART.
    # Busiz RefreshToken.blacklist() mavjud bo'lmaydi va /auth/logout/ 500 qaytaradi.
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    'django_celery_beat',
]

# django-extensions faqat dev/CI'da o'rnatiladi (requirements-dev.txt)
try:
    import django_extensions  # noqa: F401
    THIRD_PARTY_APPS.append('django_extensions')
except ImportError:
    pass

LOCAL_APPS = [
    'apps.accounts',
    'apps.products',
    'apps.inventory',
    'apps.suppliers',
    'apps.customers',
    'apps.sales',
    'apps.debts',
    'apps.expenses',
    'apps.reports',
    'apps.notifications',
    'apps.audit',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise: static fayllarni Django konteyneri o'zi (siqilgan + hashlangan) beradi
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
# Default: PostgreSQL. Faqat lokal tez sinov uchun USE_SQLITE=True qo'yish mumkin.
USE_SQLITE = config('USE_SQLITE', default=False, cast=bool)
RUNNING_TESTS = 'test' in sys.argv or 'pytest' in sys.argv[0]

if USE_SQLITE:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DATABASE_NAME', default='alkagol_db'),
            'USER': config('DATABASE_USER', default='alkagol_user'),
            'PASSWORD': config('DATABASE_PASSWORD'),
            'HOST': config('DATABASE_HOST', default='localhost'),
            'PORT': config('DATABASE_PORT', default='5432'),
            # Persistent connections — har so'rovda yangi TCP ulanish ochilmaydi
            'CONN_MAX_AGE': config('DB_CONN_MAX_AGE', default=60, cast=int),
            'CONN_HEALTH_CHECKS': True,
            'OPTIONS': {
                'connect_timeout': 10,
            },
        }
    }

# Cache — Redis (mavjud bo'lmasa lokal xotira)
REDIS_URL = config('REDIS_URL', default='')
if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
            'KEY_PREFIX': 'alkagol',
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'uz'
TIME_ZONE = config('TIME_ZONE', default='Asia/Tashkent')
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Django 5 storage backends — prod'da WhiteNoise siqilgan + manifest storage
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': (
            'django.contrib.staticfiles.storage.StaticFilesStorage'
            if DEBUG
            else 'whitenoise.storage.CompressedManifestStaticFilesStorage'
        ),
    },
}
WHITENOISE_MAX_AGE = 31536000

# Default primary key
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000',
    cast=Csv()
)
CORS_ALLOW_CREDENTIALS = True

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '30/minute',   # Anonim (masalan login urinishlari)
        'user': '5000/day',    # Avtorizatsiyadan o'tganlar uchun limit
    },
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DATETIME_FORMAT': '%Y-%m-%dT%H:%M:%S%z',
    'DATE_FORMAT': '%Y-%m-%d',
    'EXCEPTION_HANDLER': 'config.exceptions.custom_exception_handler',
}

# SimpleJWT Configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=config('JWT_ACCESS_TOKEN_LIFETIME', default=60, cast=int)),
    'REFRESH_TOKEN_LIFETIME': timedelta(minutes=config('JWT_REFRESH_TOKEN_LIFETIME', default=1440, cast=int)),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# Celery Configuration
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/1')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/2')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Admin URL prefiksi (default 'admin'; prod'da o'zgartirish tavsiya etiladi)
ADMIN_URL = config('ADMIN_URL', default='admin').strip('/')

# DRF Spectacular (OpenAPI/Swagger)
ENABLE_API_DOCS = config('ENABLE_API_DOCS', default=True, cast=bool)
SPECTACULAR_SETTINGS = {
    'TITLE': 'Alkagol Store Management API',
    'DESCRIPTION': 'CRM + POS + Inventory + Debt Management System for Retail Alcoholic Beverage Store',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SCHEMA_PATH_PREFIX': '/api/',
}

# ---------------------------------------------------------------------------
# Logging
# Konteynerda 12-factor qoidasi: hamma narsa stdout'ga. Faylga yozish faqat
# lokal development uchun (LOG_TO_FILE=True), chunki prod'da loglarni Docker
# yig'adi va konteyner ichidagi fayl disk to'ldiradi.
# ---------------------------------------------------------------------------
LOG_LEVEL = config('LOG_LEVEL', default='DEBUG' if DEBUG else 'INFO')
LOG_TO_FILE = config('LOG_TO_FILE', default=DEBUG, cast=bool)

_app_handlers = ['console']
_handlers = {
    'console': {
        'class': 'logging.StreamHandler',
        'formatter': 'verbose',
    },
}

if LOG_TO_FILE:
    os.makedirs(BASE_DIR / 'logs', exist_ok=True)
    _handlers['file'] = {
        'class': 'logging.handlers.RotatingFileHandler',
        'filename': BASE_DIR / 'logs' / 'app.log',
        'maxBytes': 10 * 1024 * 1024,  # 10 MB
        'backupCount': 5,
        'formatter': 'verbose',
    }
    _app_handlers.append('file')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': _handlers,
    'root': {
        'handlers': ['console'],
        'level': LOG_LEVEL,
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': _app_handlers,
            'level': LOG_LEVEL,
            'propagate': False,
        },
    },
}

# Kerakli papkalarni yaratish
os.makedirs(MEDIA_ROOT, exist_ok=True)
os.makedirs(STATIC_ROOT, exist_ok=True)
