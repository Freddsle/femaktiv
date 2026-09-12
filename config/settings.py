"""Local defaults and explicit production configuration for femaktiv."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
LOCAL_DIR = BASE_DIR / ".local"
LOCAL_DIR.mkdir(mode=0o700, exist_ok=True)
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-femaktiv-local-development-only")
if not DEBUG and SECRET_KEY.startswith("django-insecure-"):
    raise ImproperlyConfigured("Set DJANGO_SECRET_KEY before using production settings.")
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]").split(",")
CSRF_TRUSTED_ORIGINS = [
    v for v in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if v
]
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "notes",
    "chats",
    "pages",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "config.middleware.PrivateResponseMiddleware",
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
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("DJANGO_DB_PATH", str(LOCAL_DIR / "db.sqlite3")),
        "OPTIONS": {"timeout": 20},
    }
}
if os.environ.get("POSTGRES_DB"):
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["POSTGRES_DB"],
        "USER": os.environ.get("POSTGRES_USER", "femaktiv"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
        "OPTIONS": {"user_attributes": ["email", "display_name"]},
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "chats:list"
LOGOUT_REDIRECT_URL = "pages:home"
LANGUAGE_CODE = "en"
LANGUAGES = [("en", "English"), ("de", "Deutsch")]
USE_I18N = True
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "Europe/Berlin"
USE_TZ = True
LANGUAGE_COOKIE_NAME = "femaktiv_language"
LANGUAGE_COOKIE_SAMESITE = "Lax"
LANGUAGE_COOKIE_HTTPONLY = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
EMAIL_BACKEND = os.environ.get(
    "DJANGO_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "1") == "1"
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "femaktiv <hello@localhost>")
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
LANGUAGE_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"
DATA_UPLOAD_MAX_MEMORY_SIZE = 65536
FEMAKTIV_AI_MODE = os.environ.get("FEMAKTIV_AI_MODE", "placeholder")
FEMAKTIV_SIGNUP_ENABLED = os.environ.get("FEMAKTIV_SIGNUP_ENABLED", "0") == "1"
if FEMAKTIV_AI_MODE not in {"placeholder", "live"}:
    raise ImproperlyConfigured("FEMAKTIV_AI_MODE must be placeholder or live.")
ANYMIZE_API_KEY = os.environ.get("ANYMIZE_API_KEY", "")
ANYMIZE_MODEL = os.environ.get("ANYMIZE_MODEL", "")
BRAVE_SEARCH_API_KEY = os.environ.get("BRAVE_SEARCH_API_KEY", "")
# Account-level setting, never a fabricated per-request ZDR parameter.
ANYMIZE_ZDR_CONFIRMED = os.environ.get("ANYMIZE_ZDR_CONFIRMED", "0") == "1"
ANYMIZE_FALLBACKS_DISABLED_CONFIRMED = (
    os.environ.get("ANYMIZE_FALLBACKS_DISABLED_CONFIRMED", "0") == "1"
)


def _positive_limit(name, default):
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError:
        raise ImproperlyConfigured(f"{name} must be a positive integer.") from None
    if value < 1:
        raise ImproperlyConfigured(f"{name} must be a positive integer.")
    return value


FEMAKTIV_LIVE_USER_HOURLY_LIMIT = _positive_limit("FEMAKTIV_LIVE_USER_HOURLY_LIMIT", 30)
FEMAKTIV_LIVE_DAILY_LIMIT = _positive_limit("FEMAKTIV_LIVE_DAILY_LIMIT", 100)
CSRF_FAILURE_VIEW = "config.views.csrf_failure"
# HTTP is allowed only for a loopback-bound local production preview.
if os.environ.get("DJANGO_LOCAL_HTTP", "0") == "1":
    if set(ALLOWED_HOSTS) - {"localhost", "127.0.0.1", "[::1]"}:
        raise ImproperlyConfigured("Local HTTP preview must use loopback hosts only.")
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    LANGUAGE_COOKIE_SECURE = False
    SECURE_SSL_REDIRECT = False
    SECURE_HSTS_SECONDS = 0
# Only enable when a trusted reverse proxy sets and sanitizes this header.
if os.environ.get("DJANGO_TRUST_PROXY", "0") == "1":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
