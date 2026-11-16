"""Huella de dispositivo para avisar de un ingreso desde un dispositivo nuevo (RF-25).

La huella es un HMAC del navegador (user-agent) y de la red (IP truncada a /24 o /48). Nunca se
guarda la IP completa: así la huella no identifica a la persona (Ley 1581 de 2012).
"""

import hashlib
import hmac
import ipaddress


def truncar_ip(ip: str) -> str:
    try:
        direccion = ipaddress.ip_address(ip.strip())
    except ValueError:
        return ""
    prefijo = 24 if direccion.version == 4 else 48
    return str(ipaddress.ip_network(f"{direccion}/{prefijo}", strict=False))


def huella_dispositivo(*, user_agent: str, ip: str, clave: str) -> str:
    material = f"{user_agent.strip()}|{truncar_ip(ip)}"
    return hmac.new(clave.encode(), material.encode(), hashlib.sha256).hexdigest()


_NAVEGADORES = (
    ("Edg/", "Edge"),
    ("Firefox/", "Firefox"),
    ("Chrome/", "Chrome"),
    ("Safari/", "Safari"),
)
_SISTEMAS = (
    ("iPhone", "iPhone"),
    ("iPad", "iPad"),
    ("Android", "Android"),
    ("Windows", "Windows"),
    ("Mac OS X", "macOS"),
    ("Linux", "Linux"),
)


def _primero_que_aparece(marcas: tuple[tuple[str, str], ...], texto: str) -> str:
    """El orden importa: el user-agent de Chrome también dice «Safari» y el de iPhone «Mac OS X»."""
    return next((nombre for marca, nombre in marcas if marca in texto), "")


def describir_navegador(user_agent: str) -> str:
    """«Chrome en Windows»: ayuda a reconocer el ingreso en el correo, sin datos personales."""
    navegador = _primero_que_aparece(_NAVEGADORES, user_agent)
    sistema = _primero_que_aparece(_SISTEMAS, user_agent)
    if not navegador and not sistema:
        return "Navegador desconocido"
    return f"{navegador or 'Navegador'} en {sistema or 'un sistema desconocido'}"
