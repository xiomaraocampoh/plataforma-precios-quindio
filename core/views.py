from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse

CLAVE_SALUD = "healthz:v1"


def _bd_ok() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return True
    except Exception:  # el health check nunca debe propagar
        return False


def _cache_ok() -> bool:
    try:
        cache.set(CLAVE_SALUD, "ok", timeout=5)
        return cache.get(CLAVE_SALUD) == "ok"
    except Exception:  # idem: un fallo de caché se informa como 503, no como 500
        return False


def healthz(request):
    """Health check para el monitor de disponibilidad (M-21): PostgreSQL y caché (Redis)."""
    bd, cache_ = _bd_ok(), _cache_ok()
    cuerpo = {
        "estado": "ok" if bd and cache_ else "error",
        "bd": "ok" if bd else "error",
        "cache": "ok" if cache_ else "error",
    }
    return JsonResponse(cuerpo, status=200 if bd and cache_ else 503)
