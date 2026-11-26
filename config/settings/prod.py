import os

from django.core.exceptions import ImproperlyConfigured

from core.despliegue import ajustar_bd_serverless, es_vercel, validar_dominios_vercel

from .base import *

DEBUG = False
# Nunca se omite el 2FA en producción, diga lo que diga el entorno
PERMITIR_PRUEBA_SIN_2FA = False
if SECRET_KEY == "insegura-solo-desarrollo":
    raise ImproperlyConfigured("Defina SECRET_KEY en producción.")

MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Vercel (ADR-0031): funciones efímeras detrás del pooler de Neon. Sin VERCEL (Render, Docker) la
# conexión persistente de base.py no cambia.
EN_VERCEL = es_vercel(os.environ)
DATABASES["default"] = ajustar_bd_serverless(DATABASES["default"], en_vercel=EN_VERCEL)

# Caché compartida entre réplicas (EC-04: escalado horizontal en quincena)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL"),
    }
}

# HTTPS obligatorio por defecto. FORZAR_HTTPS=False existe SOLO para verificar la imagen de
# producción en local sin TLS (docs/operacion/despliegue.md); en un despliegue real nunca se apaga.
FORZAR_HTTPS = env.bool("FORZAR_HTTPS", default=True)
# Orígenes con los que el proveedor sirve el sitio (https://dominio); casi todos los exigen.
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
# Dominios exactos <proyecto>.vercel.app (ADR-0031). Nunca un comodín: «.vercel.app» aceptaría
# peticiones dirigidas a cualquier proyecto ajeno alojado en Vercel.
try:
    DOMINIOS_VERCEL = validar_dominios_vercel(env.list("DOMINIOS_VERCEL", default=[]))
except ValueError as error:
    raise ImproperlyConfigured(str(error)) from error
ALLOWED_HOSTS = list(dict.fromkeys([*ALLOWED_HOSTS, *DOMINIOS_VERCEL]))
CSRF_TRUSTED_ORIGINS = list(
    dict.fromkeys([*CSRF_TRUSTED_ORIGINS, *(f"https://{d}" for d in DOMINIOS_VERCEL)])
)

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = FORZAR_HTTPS
SESSION_COOKIE_SECURE = FORZAR_HTTPS
CSRF_COOKIE_SECURE = FORZAR_HTTPS
SECURE_HSTS_SECONDS = 31536000 if FORZAR_HTTPS else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = FORZAR_HTTPS
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
