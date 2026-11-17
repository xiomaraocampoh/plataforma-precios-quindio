"""Enlace al mapa de un establecimiento (RF-09). Python puro — TDD.

OpenStreetMap no exige API key ni carga scripts de terceros en nuestras páginas: solo se enlaza.
"""

from decimal import Decimal
from urllib.parse import quote

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


def enlace_busqueda(*, direccion: str, barrio: str, municipio: str) -> str | None:
    """Búsqueda por dirección en OpenStreetMap, para locales sin coordenadas."""
    partes = [" ".join(p.split()) for p in (direccion, barrio, municipio)]
    partes = [p for p in partes if p]
    if not partes or not " ".join(direccion.split()):
        return None
    consulta = ", ".join([*partes, "Quindío", "Colombia"])
    return f"https://www.openstreetmap.org/search?query={quote(consulta, safe='')}"


def enlace_mapa(
    latitud: Decimal | None,
    longitud: Decimal | None,
    *,
    direccion: str,
    barrio: str,
    municipio: str,
) -> str | None:
    """«Ver en el mapa»: el punto exacto si hay coordenadas; si no, la búsqueda por dirección."""
    return enlace_openstreetmap(latitud, longitud) or enlace_busqueda(
        direccion=direccion, barrio=barrio, municipio=municipio
    )
