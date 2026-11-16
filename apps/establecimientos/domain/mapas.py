"""Enlace al mapa de un establecimiento (RF-09). Python puro — TDD.

OpenStreetMap no exige API key ni carga scripts de terceros en nuestras páginas: solo se enlaza.
"""

from decimal import Decimal

LATITUD_MAX = Decimal(90)
LONGITUD_MAX = Decimal(180)
ZOOM_CALLE = 18


def enlace_openstreetmap(
    latitud: Decimal | None, longitud: Decimal | None, *, zoom: int = ZOOM_CALLE
) -> str | None:
    if latitud is None or longitud is None:
        return None
    if abs(latitud) > LATITUD_MAX or abs(longitud) > LONGITUD_MAX:
        raise ValueError("Coordenadas fuera de rango.")
    lat, lon = format(latitud, "f"), format(longitud, "f")
    return f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map={zoom}/{lat}/{lon}"
