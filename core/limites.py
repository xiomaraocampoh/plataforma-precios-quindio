"""Límite de tasa sencillo sobre la caché (Redis en producción): N intentos por ventana.

Se usa en el envío y la verificación de códigos, el reenvío de la verificación y la recuperación
de contraseña. Las claves no llevan correos ni datos personales: se usa un hash.
"""

import hashlib

from django.core.cache import cache


def _clave(nombre: str, sujeto: str) -> str:
    return f"v1:limite:{nombre}:{hashlib.sha256(sujeto.encode()).hexdigest()[:32]}"


def permitir(nombre: str, sujeto: str, *, maximo: int, ventana_s: int) -> bool:
    """True si `sujeto` (IP, id de usuario, correo) no superó `maximo` en la ventana."""
    clave = _clave(nombre, sujeto)
    if cache.add(clave, 1, ventana_s):
        return True
    try:
        return cache.incr(clave) <= maximo
    except ValueError:  # la clave venció entre add e incr
        cache.set(clave, 1, ventana_s)
        return True


def ip_de(request) -> str:
    """IP del cliente. Detrás del proxy del proveedor se toma la primera de X-Forwarded-For."""
    reenviada = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return reenviada.split(",")[0].strip() or request.META.get("REMOTE_ADDR", "")
