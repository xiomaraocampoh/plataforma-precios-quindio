"""Estrategia de caché del lado lectura (EC-04, D-01).

Cache-aside con TTL corto + invalidación explícita al registrar un precio.
Las claves llevan versión para poder invalidar en bloque al cambiar el formato.
"""

from django.conf import settings
from django.core.cache import cache

VERSION_CLAVES = "v1"


def clave_comparacion(producto_id: int) -> str:
    return f"comparacion:{VERSION_CLAVES}:producto:{producto_id}"


def ttl_comparacion() -> int:
    return settings.PRECIOS["CACHE_COMPARACION_TTL"]


def invalidar_comparacion(producto_id: int) -> None:
    cache.delete(clave_comparacion(producto_id))
