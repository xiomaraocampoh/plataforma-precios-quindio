import os

from .base import *

SECRET_KEY = "solo-pruebas"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# En CI se usa PostgreSQL real (DATABASE_URL). En local, sin variable, SQLite en memoria.
if not os.environ.get("DATABASE_URL"):
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
