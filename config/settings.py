"""Настройки EasyEng.

Секреты и окружение-зависимые значения берутся из переменных окружения,
значения по умолчанию подходят для локальной разработки.
"""
import os
from pathlib import Path
from urllib.parse import unquote, urlparse

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
VAR_DIR = Path(os.environ.get("EASYENG_VAR_DIR", BASE_DIR / "var"))

DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-change-me" if DEBUG else "")
if not SECRET_KEY:
    raise ImproperlyConfigured("Задайте DJANGO_SECRET_KEY (обязателен при DJANGO_DEBUG=0)")
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
# Например: https://easyeng.example.com — нужен, если сайт открывают не с localhost
CSRF_TRUSTED_ORIGINS = [o for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o]
# Включайте за HTTPS (иначе браузер не отправит cookie по http)
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = os.environ.get("DJANGO_SECURE_COOKIES", "0") == "1"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "library",
    "dictionary",
    "vocab",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "library.context_processors.inbox",
                "vocab.context_processors.due",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

def database_from_url(url):
    """postgres://user:password@host:5432/name -> настройки Django."""
    u = urlparse(url)
    if u.scheme not in ("postgres", "postgresql"):
        raise ImproperlyConfigured(f"Неподдерживаемая СУБД в DATABASE_URL: {u.scheme}")
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(u.path.lstrip("/")),
        "USER": unquote(u.username or ""),
        "PASSWORD": unquote(u.password or ""),
        "HOST": u.hostname or "",
        "PORT": str(u.port or ""),
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
    }


# По умолчанию SQLite (удобно для разработки), с DATABASE_URL — PostgreSQL
DATABASES = {
    "default": database_from_url(os.environ["DATABASE_URL"]) if os.environ.get("DATABASE_URL") else {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": VAR_DIR / "db.sqlite3",
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": VAR_DIR / "cache",
        "TIMEOUT": 60 * 60 * 24 * 30,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = Path(os.environ.get("DJANGO_STATIC_ROOT", VAR_DIR / "static"))
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    # В продакшене — сжатие и версионирование статики (нужен collectstatic)
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage" if DEBUG
        else "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}

MEDIA_URL = "media/"
MEDIA_ROOT = VAR_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "library:list"
LOGOUT_REDIRECT_URL = "login"

# Загрузка больших книг и словарей
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
MAX_TEXT_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_DICTIONARY_UPLOAD_BYTES = 200 * 1024 * 1024

# Онлайн-словари. Ключи провайдеров — см. dictionary/providers/registry.py
EASYENG_HTTP_TIMEOUT = 8
EASYENG_MYMEMORY_EMAIL = os.environ.get("MYMEMORY_EMAIL", "")  # увеличивает дневную квоту
EASYENG_LIBRETRANSLATE_URL = os.environ.get("LIBRETRANSLATE_URL", "")
EASYENG_LIBRETRANSLATE_KEY = os.environ.get("LIBRETRANSLATE_KEY", "")
