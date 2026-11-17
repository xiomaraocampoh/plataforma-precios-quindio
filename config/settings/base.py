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
    "apps.notificaciones",  # correo transaccional (ADR-021)
    "apps.administracion",  # panel propio en /panel/ (roles, catálogo, auditoría)
    # Corte III: aquí se agregará la app de comercios al integrar el módulo comercial (EC-05).
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.cuentas.middleware.SegundoFactorMiddleware",  # RF-27: 2FA obligatoria (también API)
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
AUTH_USER_MODEL = "cuentas.Usuario"
LOGIN_URL = "cuentas:ingresar"
LOGIN_REDIRECT_URL = "comparacion:inicio"

# ---------- Correo transaccional (ADR-021): relé SMTP de Brevo en todos los entornos ----------
# Las credenciales viven solo en el entorno (.env o secretos del proveedor), nunca en el código.
# Sin EMAIL_HOST no hay a dónde enviar: el correo se imprime en la consola (respaldo seguro).
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)  # 2525 si la red bloquea el 587
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=10)
_CONSOLA = "django.core.mail.backends.console.EmailBackend"
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend" if EMAIL_HOST else _CONSOLA,
)
if not EMAIL_HOST and EMAIL_BACKEND.endswith("smtp.EmailBackend"):
    EMAIL_BACKEND = _CONSOLA
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="AhorraPues <no-responder@localhost>")
EMAIL_REPLY_TO = env("EMAIL_REPLY_TO", default="")
# Dirección pública del sitio para los enlaces de los correos (no se toma del Host de la petición)
SITIO_URL = env("SITIO_URL", default="http://localhost:8000").rstrip("/")
NOTIFICACIONES = {
    # Encolar con transaction.on_commit: el correo sale solo si la transacción se confirma
    "ENVIAR_AL_CONFIRMAR": True,
}
PASSWORD_RESET_TIMEOUT = env.int("PASSWORD_RESET_TIMEOUT", default=60 * 60)  # 1 hora
LOGOUT_REDIRECT_URL = "comparacion:inicio"

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
                "apps.administracion.context_processors.panel",
            ],
        },
    },
]

DATABASES = {
    # Obligatoria: el secreto vive solo en el entorno (.env, .env.prod o el proveedor). Sin ella el
    # arranque falla con «Set the DATABASE_URL environment variable». Ver .env.example.
    "default": env.db("DATABASE_URL"),
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
    "DEFAULT_THROTTLE_RATES": {
        # Por IP. Solo se suben para la prueba de carga (k6 simula 500 personas desde UNA sola IP);
        # en producción se dejan los valores por defecto.
        "anon": env.str("LIMITE_ANONIMO", default="120/min"),
        "user": env.str("LIMITE_USUARIO", default="240/min"),
        "reportes": "30/hour",
        "sugerencias": "10/hour",  # RF-10
        "denuncias": "20/hour",  # RF-20
        "moderacion": "600/hour",  # RF-21
    },
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
    "LIMITE_REPORTES_HORA": env.int("LIMITE_REPORTES_HORA", default=30),  # RN-10
}

INTEGRACIONES = {
    "SIPSA_BASE_URL": env.str("SIPSA_BASE_URL", default=""),
    "SIPSA_TIMEOUT_S": env.int("SIPSA_TIMEOUT_S", default=5),
    # Reconocimiento de productos por foto (ADR-022). Sin clave, la función queda apagada.
    "ANTHROPIC_API_KEY": env.str("ANTHROPIC_API_KEY", default=""),
    "RECONOCIMIENTO_MODELO": env.str("RECONOCIMIENTO_MODELO", default="claude-opus-5-5"),
    "RECONOCIMIENTO_TIMEOUT_S": env.int("RECONOCIMIENTO_TIMEOUT_S", default=20),
    "RECONOCIMIENTOS_POR_HORA": env.int("RECONOCIMIENTOS_POR_HORA", default=20),
    "RECONOCIMIENTOS_ANONIMO_POR_HORA": env.int("RECONOCIMIENTOS_ANONIMO_POR_HORA", default=10),
    "RECONOCIMIENTOS_POR_DIA_TOTAL": env.int("RECONOCIMIENTOS_POR_DIA_TOTAL", default=300),
}
