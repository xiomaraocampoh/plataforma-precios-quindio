"""Configuración común a todos los entornos."""

from pathlib import Path

import environ

from core.correo import elegir_backend_correo

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
    "apps.comercios",  # Comercios (Corte III, ADR-012): se integra por el puerto de comparacion
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
# Con BREVO_API_KEY el correo sale por la API HTTPS de Brevo (puerto 443): Render gratuito bloquea
# los puertos SMTP. Sin ella, SMTP si hay EMAIL_HOST; si no, la consola (core/correo.py).
BREVO_API_KEY = env("BREVO_API_KEY", default="")
EMAIL_BACKEND = elegir_backend_correo(
    brevo_api_key=BREVO_API_KEY,
    email_host=EMAIL_HOST,
    explicito=env("EMAIL_BACKEND", default=""),
)
ANYMAIL = {"BREVO_API_KEY": BREVO_API_KEY} if BREVO_API_KEY else {}
# Reintentos sin worker: un cron externo llama POST /interno/correos/procesar/ con este token
CORREO_CRON_TOKEN = env("CORREO_CRON_TOKEN", default="")
CORREOS_POR_PASADA = env.int("CORREOS_POR_PASADA", default=50)
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
        "correos_cron": "30/hour",  # POST /interno/correos/procesar/ (cron cada 10 min)
        # Escáner en vivo (ADR-0026): un fotograma cada 1,5 s como máximo ≈ 40 por minuto
        "escaneo": env.str("LIMITE_ESCANEO", default="40/min"),
        # Portal y API de comercios (RF-C03 a RF-C07): escrituras por persona
        "comercios": f"{env.int('COMERCIO_ESCRITURAS_POR_HORA', default=60)}/hour",
    },
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# Módulo comercial (Corte III, ADR-012 a ADR-018). Mismo tope en el portal HTMX y en la API.
COMERCIOS = {"ESCRITURAS_POR_HORA": env.int("COMERCIO_ESCRITURAS_POR_HORA", default=60)}

SPECTACULAR_SETTINGS = {
    "TITLE": "API Plataforma Colaborativa de Precios — Quindío",
    "DESCRIPTION": "Registro, consulta y comparación neutral de precios de la canasta familiar.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    # El «tipo» de la promoción choca de nombre con otros «tipo» del esquema
    "ENUM_NAME_OVERRIDES": {
        "TipoEnum": "apps.establecimientos.models.Establecimiento.Tipo",  # nombre de siempre
        "TipoPromocionEnum": "apps.comercios.models.Promocion.Tipo",
    },
}

# Solo en local: las cuentas de crear_cuentas_prueba entran sin segundo paso si DEBUG=True y este
# ajuste está activo. prod.py lo fija en False; el arranque avisa en consola (cuentas.W001).
PERMITIR_PRUEBA_SIN_2FA = env.bool("PERMITIR_PRUEBA_SIN_2FA", default=False)

# Siembra de datos de prueba al correr `migrate` (ADR-0023). Con DEBUG=True siempre se siembra;
# con DEBUG=False (producción) solo si se pide explícitamente. Las cuentas van aparte porque son
# cuentas con rol conocido y una contraseña compartida (CUENTAS_PRUEBA_PASSWORD).
SEMBRAR_DATOS_PRUEBA = env.bool("SEMBRAR_DATOS_PRUEBA", default=False)
SEMBRAR_CUENTAS_PRUEBA = env.bool("SEMBRAR_CUENTAS_PRUEBA", default=False)
# Buzón real del equipo para las cuentas de prueba (parte_local+sufijo@dominio): ahí llegan los
# códigos del 2FA. Vacío: correos @example.com (apps/cuentas/domain/cuentas_prueba.py).
CUENTAS_PRUEBA_CORREO_BASE = env("CUENTAS_PRUEBA_CORREO_BASE", default="")

# Búsqueda por foto: puntaje mínimo (0 a 1) para proponer un producto (catalogo/domain/coincidencia)
UMBRAL_COINCIDENCIA_FOTO = env.float("UMBRAL_COINCIDENCIA_FOTO", default=0.45)

# Reglas de negocio parametrizables (ver docs/adr/0003-vigencia-de-precios.md)
PRECIOS = {
    "VIGENCIA_REPORTE_DIAS": env.int("VIGENCIA_REPORTE_DIAS", default=7),
    "VIGENCIA_PERECEDERO_DIAS": env.int("VIGENCIA_PERECEDERO_DIAS", default=3),
    "VIGENCIA_OFICIAL_DIAS": env.int("VIGENCIA_OFICIAL_DIAS", default=30),
    "CACHE_COMPARACION_TTL": env.int("CACHE_COMPARACION_TTL", default=60),  # D-01 ≤ 1 min
    "TOLERANCIA_ANOMALIA": env.str("TOLERANCIA_ANOMALIA", default="0.5"),
    "LIMITE_REPORTES_HORA": env.int("LIMITE_REPORTES_HORA", default=30),  # RN-10
}

# Política de tratamiento de datos (Ley 1581 de 2012, ADR-0008 y ADR-022): quién responde y por
# dónde se consulta o reclama. El correo se puede cambiar por entorno; vacío = no se muestra.
POLITICA_DATOS = {
    "RESPONSABLE": env.str(
        "POLITICA_DATOS_RESPONSABLE",
        default=(
            "el equipo del proyecto AhorraPues (Ingeniería de Software, "
            "Corporación Universitaria Empresarial Alexander von Humboldt, Armenia, Quindío)"
        ),
    ),
    "CORREO_CONTACTO": env.str("POLITICA_DATOS_CORREO", default="ahorrapuescolombia@gmail.com"),
}

INTEGRACIONES = {
    "SIPSA_BASE_URL": env.str("SIPSA_BASE_URL", default=""),
    "SIPSA_TIMEOUT_S": env.int("SIPSA_TIMEOUT_S", default=5),
    # promediosSipsaCiudad trae ~120 MB (todas las ciudades e historial): tarda ~1 min
    "SIPSA_SOAP_TIMEOUT_S": env.int("SIPSA_SOAP_TIMEOUT_S", default=180),
    # Reconocimiento de productos por foto (ADR-022). Sin clave, la función queda apagada.
    "ANTHROPIC_API_KEY": env.str("ANTHROPIC_API_KEY", default=""),
    "RECONOCIMIENTO_MODELO": env.str("RECONOCIMIENTO_MODELO", default="claude-opus-5-5"),
    "RECONOCIMIENTO_TIMEOUT_S": env.int("RECONOCIMIENTO_TIMEOUT_S", default=20),
    "RECONOCIMIENTOS_POR_HORA": env.int("RECONOCIMIENTOS_POR_HORA", default=60),
    "RECONOCIMIENTOS_ANONIMO_POR_HORA": env.int("RECONOCIMIENTOS_ANONIMO_POR_HORA", default=10),
    "RECONOCIMIENTOS_POR_DIA_TOTAL": env.int("RECONOCIMIENTOS_POR_DIA_TOTAL", default=300),
    # Escáner en vivo (ADR-0026): apagado por defecto; además exige ANTHROPIC_API_KEY. Cada
    # fotograma enviado consume el mismo cupo por hora y por día que una foto.
    "ESCANEO_VIVO_ACTIVO": env.bool("ESCANEO_VIVO_ACTIVO", default=False),
    "RECONOCIMIENTO_MODELO_VIVO": env.str("RECONOCIMIENTO_MODELO_VIVO", default="claude-haiku-5-5"),
    "RECONOCIMIENTO_TIMEOUT_VIVO_S": env.int("RECONOCIMIENTO_TIMEOUT_VIVO_S", default=6),
    "ESCANEO_MAX_FOTOGRAMAS_SESION": env.int("ESCANEO_MAX_FOTOGRAMAS_SESION", default=20),
    "ESCANEO_INTERVALO_MS": env.int("ESCANEO_INTERVALO_MS", default=1500),
    "PRECIO_MAXIMO_ETIQUETA": env.str("PRECIO_MAXIMO_ETIQUETA", default="2000000"),
}
