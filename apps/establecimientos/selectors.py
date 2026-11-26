"""Lecturas del directorio de establecimientos (RF-08, RF-09)."""

from .domain.coincidencia import elegir_establecimiento
from .domain.mapas import enlace_openstreetmap
from .models import Establecimiento


def _aprobados():
    return Establecimiento.objects.filter(activo=True, estado=Establecimiento.Estado.APROBADO)


def directorio(*, municipio: str = "", barrio: str = "", tipo: str = "") -> list[Establecimiento]:
    """Establecimientos aprobados y activos; los filtros solo reducen. Orden alfabético."""
    qs = _aprobados()
    if municipio:
        qs = qs.filter(municipio__iexact=municipio)
    if barrio:
        qs = qs.filter(barrio__iexact=barrio)
    if tipo:
        qs = qs.filter(tipo=tipo)
    establecimientos = list(qs.order_by("nombre"))
    for e in establecimientos:
        e.enlace_mapa = enlace_openstreetmap(e.latitud, e.longitud)
    return establecimientos


def establecimiento_publico(pk: int) -> Establecimiento | None:
    """Un establecimiento aprobado y activo, o None (el público no ve pendientes ni inactivos)."""
    e = _aprobados().filter(pk=pk).first()
    if e is not None:
        e.enlace_mapa = enlace_openstreetmap(e.latitud, e.longitud)
    return e


def opciones_directorio(municipio: str = "") -> dict:
    aprobados = _aprobados()
    barrios = aprobados.exclude(barrio="")
    if municipio:
        barrios = barrios.filter(municipio__iexact=municipio)
    return {
        "municipios": list(
            aprobados.order_by("municipio").values_list("municipio", flat=True).distinct()
        ),
        "barrios": list(barrios.order_by("barrio").values_list("barrio", flat=True).distinct()),
        "tipos": Establecimiento.Tipo.choices,
    }


def pendientes():
    return (
        Establecimiento.objects.filter(estado=Establecimiento.Estado.PENDIENTE)
        .select_related("sugerido_por")
        .order_by("creado_en")
    )


def establecimiento_de_etiqueta(texto: str) -> Establecimiento | None:
    """La tienda del directorio que nombra una etiqueta de precio, solo si es una sin dudas
    (ADR-0026). Un query: el directorio de Armenia cabe en memoria."""
    if not texto:
        return None
    candidatos = _aprobados().values_list("pk", "nombre")
    pk = elegir_establecimiento(texto, candidatos)
    return _aprobados().filter(pk=pk).first() if pk else None
