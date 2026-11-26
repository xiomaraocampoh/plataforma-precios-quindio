"""Estrategia de caché del lado lectura (EC-04, D-01).

Cache-aside con TTL corto + invalidación explícita al registrar un precio.
Las claves llevan versión para poder invalidar en bloque al cambiar el formato.
"""

from django.conf import settings
from django.core.cache import cache

# v3: FilaComparacion trae los datos del módulo comercial (ADR-012); v2 ya no se lee
VERSION_CLAVES = "v3"


def clave_comparacion(producto_id: int) -> str:
    return f"comparacion:{VERSION_CLAVES}:producto:{producto_id}"


def clave_resumen() -> str:
    return f"resumen:{VERSION_CLAVES}"


def ttl_comparacion() -> int:
    return settings.PRECIOS["CACHE_COMPARACION_TTL"]


def invalidar_comparacion(producto_id: int) -> None:
    cache.delete_many([clave_comparacion(producto_id), clave_resumen()])
