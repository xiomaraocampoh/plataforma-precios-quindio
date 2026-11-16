"""Lecturas del directorio de establecimientos (RF-08, RF-09)."""

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
