import os
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key


BASE_DIR = Path(__file__).resolve().parent.parent

IS_VERCEL = os.environ.get("VERCEL", "").lower() in {"1", "true", "yes"}
DEBUG = os.environ.get(
    "DJANGO_DEBUG",
    "false" if IS_VERCEL else "true",
).lower() == "true"
if IS_VERCEL and DEBUG:
    raise ImproperlyConfigured("DJANGO_DEBUG must be false on Vercel.")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("Set DJANGO_SECRET_KEY when DEBUG is disabled.")
    SECRET_KEY = get_random_secret_key()

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "DJANGO_ALLOWED_HOSTS",
        "127.0.0.1,localhost",
    ).split(",")
    if host.strip()
]
VERCEL_HOSTS = (
    os.environ.get("VERCEL_URL", ""),
    os.environ.get("VERCEL_PROJECT_PRODUCTION_URL", ""),
    "pizza-web-app-six.vercel.app",
)
if IS_VERCEL:
    for host in VERCEL_HOSTS:
        host = host.strip()
        if host and host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(host)
if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured("Set DJANGO_ALLOWED_HOSTS when DEBUG is disabled.")

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
if IS_VERCEL:
    for host in VERCEL_HOSTS:
        host = host.strip()
        if host.startswith("https://"):
            host = host[len("https://"):]
        elif host.startswith("http://"):
            host = host[len("http://"):]
        host = host.rstrip("/")
        if host:
            origin = f"https://{host}"
            if origin not in CSRF_TRUSTED_ORIGINS:
                CSRF_TRUSTED_ORIGINS.append(origin)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "ordering",
]

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "ordering.staticfiles.ProjectRootAssetsFinder",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "pizzaslice_backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "pizzaslice_backend.wsgi.application"

POSTGRES_ENV_VARS = (
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
    "DB_HOST",
    "DB_PORT",
)
USE_SQLITE = os.environ.get("USE_SQLITE", "").lower() in {"1", "true", "yes"}
REQUIRES_POSTGRES = IS_VERCEL or not DEBUG
DATABASE_CONFIG = {
    name: os.environ.get(name, "").strip()
    for name in POSTGRES_ENV_VARS
}
DATABASE_URL = (
    os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or ""
).strip()
HAS_POSTGRES_CONFIG = any(DATABASE_CONFIG.values())


def postgres_database_from_url(database_url):
    try:
        parsed_url = urlsplit(database_url)
        port = parsed_url.port
    except ValueError as error:
        raise ImproperlyConfigured(
            "DATABASE_URL or POSTGRES_URL has an invalid host or port."
        ) from error
    if port is not None and not 1 <= port <= 65535:
        raise ImproperlyConfigured(
            "DATABASE_URL or POSTGRES_URL has an invalid port."
        )

    if parsed_url.scheme not in {"postgres", "postgresql"}:
        raise ImproperlyConfigured(
            "DATABASE_URL or POSTGRES_URL must use postgres:// or postgresql://."
        )

    database_name = unquote(parsed_url.path.lstrip("/"))
    missing_url_parts = []
    if not parsed_url.hostname:
        missing_url_parts.append("host")
    if not parsed_url.username:
        missing_url_parts.append("user")
    if not parsed_url.password:
        missing_url_parts.append("password")
    if not database_name:
        missing_url_parts.append("database name")
    if missing_url_parts:
        raise ImproperlyConfigured(
            "DATABASE_URL or POSTGRES_URL is missing: "
            + ", ".join(missing_url_parts)
            + "."
        )

    options = {
        name: values[-1]
        for name, values in parse_qs(parsed_url.query).items()
        if name in {
            "application_name",
            "connect_timeout",
            "sslmode",
            "sslrootcert",
            "sslcert",
            "sslkey",
        }
    }
    database = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": database_name,
        "USER": unquote(parsed_url.username),
        "PASSWORD": unquote(parsed_url.password),
        "HOST": parsed_url.hostname,
        "PORT": port or 5432,
    }
    if options:
        database["OPTIONS"] = options
    return database


if USE_SQLITE and DEBUG and not IS_VERCEL:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
elif all(DATABASE_CONFIG.values()):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": DATABASE_CONFIG["DB_NAME"],
            "USER": DATABASE_CONFIG["DB_USER"],
            "PASSWORD": DATABASE_CONFIG["DB_PASSWORD"],
            "HOST": DATABASE_CONFIG["DB_HOST"],
            "PORT": DATABASE_CONFIG["DB_PORT"],
        }
    }
elif DATABASE_URL:
    DATABASES = {"default": postgres_database_from_url(DATABASE_URL)}
elif REQUIRES_POSTGRES or HAS_POSTGRES_CONFIG:
    missing_database_vars = [
        var for var in POSTGRES_ENV_VARS if not DATABASE_CONFIG[var]
    ]
    raise ImproperlyConfigured(
        "PostgreSQL is required, but the configuration is incomplete. "
        f"Missing variables: {', '.join(missing_database_vars)}. "
        "Set all five DB_* variables or provide DATABASE_URL or POSTGRES_URL."
    )
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Accra"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = []
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31_536_000 if IS_VERCEL and not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

if IS_VERCEL:
    # Vercel terminates TLS and forwards the original request protocol.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
