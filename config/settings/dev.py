from .base import *

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Con docker compose (REDIS_URL definido) el desarrollo usa la misma caché que producción
# (ADR-0004); sin la variable se mantiene la caché en memoria para arrancar sin Docker.
if env("REDIS_URL", default=""):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": env("REDIS_URL"),
        }
    }
