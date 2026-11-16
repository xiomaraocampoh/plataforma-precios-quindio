"""Privacidad en los registros (logs): nunca el correo completo (Ley 1581 de 2012)."""


def enmascarar_correo(correo: str) -> str:
    """«lucia@example.com» → «l***@e***.com»."""
    if not correo:
        return "(sin correo)"
    usuario, _, dominio = correo.partition("@")
    nombre, punto, tld = dominio.rpartition(".")
    if not usuario or not nombre or not punto:
        return "***"
    return f"{usuario[0]}***@{nombre[0]}***.{tld}"
