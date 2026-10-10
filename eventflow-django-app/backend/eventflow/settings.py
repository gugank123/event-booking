"""
Django settings for the EventFlow project.
"""
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load backend/.env so local config (DB credentials, OAuth IDs, mail) just works.
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-secret-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "accounts",
    "events",
    "bookings",
    "comms",
    "payments",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "eventflow.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "eventflow.wsgi.application"

# MySQL is the database. Connection values come from one of (first set wins):
#   1. DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD (e.g. Railway TCP proxy)
#   2. MYSQL_URL (e.g. Railway/Aiven connection string)
#   3. MYSQL_DATABASE/MYSQL_USER/MYSQL_PASSWORD/MYSQL_HOST/MYSQL_PORT (local)
# Aiven MySQL *requires* SSL with its CA certificate, so this block also
# supports MYSQL_SSL_CA / MYSQL_SSL_CA_CONTENT (see below).
# Driver is mysqlclient (MySQLdb). If it is ever missing on a host, the
# PyMySQL fallback below keeps the app booting with the same ENGINE.
import dj_database_url
import tempfile

try:
    import MySQLdb  # noqa: F401  (mysqlclient — the production driver)

    _DB_DRIVER = "mysqlclient"
except ImportError:  # pragma: no cover
    import pymysql

    pymysql.install_as_MySQLdb()
    _DB_DRIVER = "pymysql-fallback"


def _mysql_options():
    """Build OPTIONS dict for Django's MySQL backend, with Aiven SSL if configured."""
    options = {"charset": "utf8mb4"}
    # Path to Aiven's ca.pem, or the PEM content itself. Both work so the same
    # env vars function locally (file path) and on Render (paste content as
    # a secret env var, since Render has no file upload for the CA).
    ssl_ca = os.environ.get("MYSQL_SSL_CA", "").strip()
    ssl_ca_content = os.environ.get("MYSQL_SSL_CA_CONTENT", "").strip()
    ca_file = None
    ca_dest = Path(os.environ.get("MYSQL_SSL_CA_FILE", str(Path(tempfile.gettempdir()) / "aiven-ca.pem")))
    if ssl_ca_content.startswith("-----BEGIN"):
        # Cert pasted directly into env var -> materialise as a file.
        ca_file = ca_dest
        try:
            ca_file.parent.mkdir(parents=True, exist_ok=True)
            if not ca_file.exists() or ca_file.read_text() != ssl_ca_content:
                ca_file.write_text(ssl_ca_content)
        except OSError:
            ca_file = None
    elif ssl_ca.startswith("-----BEGIN"):
        ca_file = ca_dest
        try:
            ca_file.parent.mkdir(parents=True, exist_ok=True)
            if not ca_file.exists() or ca_file.read_text() != ssl_ca:
                ca_file.write_text(ssl_ca)
        except OSError:
            ca_file = None
    elif ssl_ca:
        candidate = Path(ssl_ca)
        if candidate.is_file():
            ca_file = candidate
    # Local dev convenience: backend/ca.pem (downloaded from Aiven console)
    # is picked up automatically if no env var is set.
    if ca_file is None:
        local_ca = BASE_DIR / "ca.pem"
        if local_ca.is_file() and (
            os.environ.get("MYSQL_URL", "")
            or "aivencloud" in os.environ.get("MYSQL_HOST", "")
            or "aivencloud" in os.environ.get("DB_HOST", "")
        ):
            ca_file = local_ca
    if ca_file is not None:
        options["ssl"] = {"ca": str(ca_file)}
    return options


if os.environ.get("DB_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.environ.get("DB_NAME", "railway"),
            "USER": os.environ.get("DB_USER", "root"),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "HOST": os.environ["DB_HOST"],
            "PORT": os.environ.get("DB_PORT", "3306"),
            "OPTIONS": _mysql_options(),
            "TEST": {"CHARSET": "utf8mb4"},
            "CONN_MAX_AGE": 60,
            "CONN_HEALTH_CHECKS": True,
        }
    }
elif os.environ.get("MYSQL_URL"):
    DATABASES = {"default": dj_database_url.parse(os.environ["MYSQL_URL"], conn_max_age=60)}
    DATABASES["default"]["OPTIONS"] = _mysql_options()
    DATABASES["default"]["TEST"] = {"CHARSET": "utf8mb4"}
    DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.environ.get("MYSQL_DATABASE", "eventflow"),
            "USER": os.environ.get("MYSQL_USER", "eventflow"),
            "PASSWORD": os.environ.get("MYSQL_PASSWORD", ""),
            "HOST": os.environ.get("MYSQL_HOST", "127.0.0.1"),
            "PORT": os.environ.get("MYSQL_PORT", "3306"),
            "OPTIONS": _mysql_options(),
            "TEST": {"CHARSET": "utf8mb4"},
        }
    }

import logging as _logging

_logging.getLogger(__name__).info(
    "DB driver=%s host=%s db=%s", _DB_DRIVER,
    (DATABASES["default"].get("HOST") or "?"), DATABASES["default"].get("NAME"),
)

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# Uploaded event posters. Served by Django in development; use object storage
# (S3/GCS) via DEFAULT_FILE_STORAGE in production.
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Behind Render/Vercel the app is served over HTTPS via a proxy.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"
    # NOTE: HTTPS redirect itself is handled by Render's proxy; enabling
    # SECURE_SSL_REDIRECT here would risk redirect loops behind proxies.

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ),
    "DEFAULT_PAGINATION_CLASS": None,
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/minute",
        "user": "300/minute",
        "auth": "10/minute",
        "email": "5/hour",
    },
    "EXCEPTION_HANDLER": "eventflow.exceptions.custom_exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "EventFlow API",
    "DESCRIPTION": "Event ticketing & seat booking platform — auth, events, holds, bookings, Razorpay payments + webhook, tickets, coupons, support.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

# Google Sign-In: OAuth 2.0 Client ID the backend trusts when verifying
# ID tokens sent to POST /api/auth/google/. Get one at
# https://console.cloud.google.com/apis/credentials (OAuth client, Web app).
GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")

# Email confirmations. Default is the console backend (prints mail to the
# Django server log) so local dev works with zero setup. To send real mail
# (e.g. Gmail), set EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
# plus EMAIL_HOST/PORT/USER/PASSWORD (Gmail needs an App Password).
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "true").lower() == "true"
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "EventFlow <noreply@eventflow.dev>")

# Public web address of the React app, used to build links inside emails.
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173").rstrip("/")

# Optional public contact details shown on the Support page (never hard-code
# personal addresses in code — configure here via environment).
SUPPORT_EMAIL = os.environ.get("SUPPORT_EMAIL", "support@eventflow.dev")
SUPPORT_PHONE = os.environ.get("SUPPORT_PHONE", "")

# The React dev server's origin. Add your deployed frontend URL in production.
CORS_ALLOWED_ORIGINS = os.environ.get(
    "CORS_ALLOWED_ORIGINS", "http://localhost:5173"
).split(",")

# --- Production payments (Razorpay, INR) ---
# Secret keys live ONLY in backend env vars — never expose to React.
PAYMENT_PROVIDER = os.environ.get("PAYMENT_PROVIDER", "razorpay")
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", os.environ.get("PAYMENT_KEY_ID", ""))
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", os.environ.get("PAYMENT_KEY_SECRET", ""))
RAZORPAY_WEBHOOK_SECRET = os.environ.get("RAZORPAY_WEBHOOK_SECRET", os.environ.get("PAYMENT_WEBHOOK_SECRET", ""))
# Comma-separated list of trusted webhook source IPs (optional extra check).
PAYMENT_WEBHOOK_ALLOWED_IPS = [
    ip.strip() for ip in os.environ.get("PAYMENT_WEBHOOK_ALLOWED_IPS", "").split(",") if ip.strip()
]

# --- Booking money math ---
PLATFORM_FEE_PERCENT = float(os.environ.get("PLATFORM_FEE_PERCENT", "2.0"))
TAX_PERCENT = float(os.environ.get("TAX_PERCENT", "0.0"))
SEAT_HOLD_MINUTES = int(os.environ.get("SEAT_HOLD_MINUTES", "8"))
CANCELLATION_WINDOW_HOURS = int(os.environ.get("CANCELLATION_WINDOW_HOURS", "24"))

# --- Structured logging (never log secrets / card data) ---
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"default": {"format": "[{levelname}] {asctime} {name}: {message}", "style": "{"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "default"}},
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
}

# Test runs disable API throttling (repeated logins in tests are not abuse).
import sys as _sys

if "test" in _sys.argv:
    REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []
    REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
        "anon": "10000/minute", "user": "10000/minute",
        "auth": "10000/minute", "email": "10000/minute",
    }



