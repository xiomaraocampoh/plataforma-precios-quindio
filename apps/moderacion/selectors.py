"""Lecturas de moderación: la bandeja (RF-21) y el estado de las denuncias de cada usuario."""

from apps.catalogo.models import SolicitudCatalogo
from apps.establecimientos import selectors as establecimientos
from apps.precios.models import ReportePrecio

from .models import DecisionModeracion, Denuncia


def bandeja() -> dict:
    """Pendientes de moderación. Solo la ven moderadores; incluye al autor para poder suspender."""
    reportes = (
        ReportePrecio.objects.filter(estado=ReportePrecio.Estado.EN_REVISION)
        .select_related("presentacion__producto__marca", "establecimiento", "autor")
        .order_by("creado_en")
    )
    denuncias = (
        Denuncia.objects.filter(estado=Denuncia.Estado.ABIERTA)
        .select_related(
            "reporte__presentacion__producto", "reporte__establecimiento", "reporte__autor"
        )
        .order_by("creado_en")
    )
    solicitudes = (
        SolicitudCatalogo.objects.filter(estado=SolicitudCatalogo.Estado.PENDIENTE)
        .select_related("categoria", "solicitante")
        .order_by("creado_en")
    )
    return {
        "reportes": list(reportes),
        "denuncias": list(denuncias),
        "solicitudes": list(solicitudes),
        "establecimientos": list(establecimientos.pendientes()),
        "decisiones": list(
            DecisionModeracion.objects.select_related("moderador").order_by("-creado_en")[:10]
        ),
    }


def reportes_en_revision():
    return (
        ReportePrecio.objects.filter(estado=ReportePrecio.Estado.EN_REVISION)
        .select_related("presentacion__producto__marca", "establecimiento")
        .order_by("creado_en")
    )


def denunciados_por(usuario, reporte_ids: list[int]) -> set[int]:
    return set(
        Denuncia.objects.filter(denunciante=usuario, reporte_id__in=reporte_ids).values_list(
            "reporte_id", flat=True
        )
    )
