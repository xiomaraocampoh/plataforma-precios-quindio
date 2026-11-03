"""Configuración común a todos los entornos."""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(DEBUG=(bool, False))
if (BASE_DIR / ".env").exists():
    environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="insegura-solo-desarrollo")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]
THIRD_PARTY_APPS = [
    "rest_framework",
    "drf_spectacular",
    "django_htmx",
]
# Monolito modular: cada app es un módulo de dominio con sus capas.
LOCAL_APPS = [
    "core",
    "apps.cuentas",
    "apps.catalogo",
    "apps.establecimientos",
    "apps.precios",  # Reportantes
    "apps.comparacion",  # Consumidores (lado lectura)
    "apps.moderacion",
    "apps.integraciones",
    # "apps.comercios",      # Corte III — se activa al integrar el módulo comercial (EC-05)
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
AUTH_USER_MODEL = "cuentas.Usuario"
LOGIN_URL = "admin:login"  # provisional hasta construir el flujo de cuentas (Corte II)

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
            ],
        },
    },
]

DATABASES = {
    "default": env.db("DATABASE_URL", default="postgres://precios:precios@localhost:5432/precios"),
}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
}

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticatedOrReadOnly"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    # Resistencia (M-16) ante reportes masivos / coordinados (EC-03)
    "DEFAULT_THROTTLE_RATES": {"anon": "120/min", "user": "240/min", "reportes": "30/hour"},
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "API Plataforma Colaborativa de Precios — Quindío",
    "DESCRIPTION": "Registro, consulta y comparación neutral de precios de la canasta familiar.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# Reglas de negocio parametrizables (ver docs/adr/0003-vigencia-de-precios.md)
PRECIOS = {
    "VIGENCIA_REPORTE_DIAS": env.int("VIGENCIA_REPORTE_DIAS", default=7),
    "VIGENCIA_PERECEDERO_DIAS": env.int("VIGENCIA_PERECEDERO_DIAS", default=3),
    "VIGENCIA_OFICIAL_DIAS": env.int("VIGENCIA_OFICIAL_DIAS", default=30),
    "CACHE_COMPARACION_TTL": env.int("CACHE_COMPARACION_TTL", default=60),  # D-01 ≤ 1 min
    "TOLERANCIA_ANOMALIA": env.str("TOLERANCIA_ANOMALIA", default="0.5"),
}

INTEGRACIONES = {
    "SIPSA_BASE_URL": env.str("SIPSA_BASE_URL", default=""),
    "SIPSA_TIMEOUT_S": env.int("SIPSA_TIMEOUT_S", default=5),
}
