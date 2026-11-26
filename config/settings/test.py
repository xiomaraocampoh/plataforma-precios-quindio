import os

from .base import *

SECRET_KEY = "solo-pruebas"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# En CI se usa PostgreSQL real (DATABASE_URL). En local, sin variable, SQLite en memoria.
if not os.environ.get("DATABASE_URL"):
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# Las pruebas y el CI nunca salen a la red: el correo queda en django.core.mail.outbox
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
BREVO_API_KEY = ""  # aunque el .env tenga una clave real, las pruebas nunca la usan
ANYMAIL = {}
CORREO_CRON_TOKEN = ""
EMAIL_HOST = ""
EMAIL_HOST_PASSWORD = ""
SITIO_URL = "http://testserver"
EMAIL_REPLY_TO = "respuestas@ahorrapues.test"
DEFAULT_FROM_EMAIL = "AhorraPues <no-responder@ahorrapues.test>"
# La transacción de cada prueba nunca se confirma: aquí el envío ocurre al encolar. El camino con
# transaction.on_commit se prueba aparte (tests/integration/notificaciones/test_outbox.py).
NOTIFICACIONES = {"ENVIAR_AL_CONFIRMAR": False}

# La base de pruebas nace vacía aunque el .env active la siembra (ADR-0023): las pruebas de la
# siembra la activan con override_settings.
SEMBRAR_DATOS_PRUEBA = False
SEMBRAR_CUENTAS_PRUEBA = False
CUENTAS_PRUEBA_CORREO_BASE = ""  # las pruebas y el CI siempre con @example.com
