"""Lecturas del módulo precios (capa de aplicación).

`politica_vigencia` traduce la configuración (settings.PRECIOS, ADR-0003) a la política de
dominio. Vive aquí para que servicios de escritura y selectores de otros módulos usen la misma.
"""

from datetime import datetime

from django.conf import settings
from django.db.models import Count, Exists, Max, OuterRef, Q
from django.utils import timezone

from apps.catalogo import selectors as catalogo

from .domain.vigencia import PoliticaVigencia
from .models import ConfirmacionPrecio, ReportePrecio


def politica_vigencia() -> PoliticaVigencia:
    p = settings.PRECIOS
    return PoliticaVigencia(
        dias_reporte=p["VIGENCIA_REPORTE_DIAS"],
        dias_perecedero=p["VIGENCIA_PERECEDERO_DIAS"],
        dias_oficial=p["VIGENCIA_OFICIAL_DIAS"],
    )


def contar_aportes(usuario) -> int:
    """Reportes del usuario (cualquier estado). Para «Mis datos» y «Mis aportes»."""
    return ReportePrecio.objects.filter(autor=usuario).count()


def listar_aportes(usuario):
    """«Mis aportes»: reportes del usuario con su estado, del más reciente al más antiguo."""
    return (
        ReportePrecio.objects.filter(autor=usuario)
        .select_related("presentacion__producto__marca", "establecimiento")
        .order_by("-creado_en")
    )


def confirmaciones_por_reporte(reporte_ids: list[int]) -> dict[int, tuple[int, datetime]]:
    """{reporte_id: (número de confirmaciones, la más reciente)} en un solo query (RF-14)."""
    filas = (
        ConfirmacionPrecio.objects.filter(reporte_id__in=reporte_ids)
        .values("reporte_id")
        .annotate(n=Count("id"), ultima=Max("creado_en"))
    )
    return {f["reporte_id"]: (f["n"], f["ultima"]) for f in filas}


def confirmados_hoy(usuario, reporte_ids: list[int]) -> set[int]:
    return set(
        ConfirmacionPrecio.objects.filter(
            usuario=usuario, reporte_id__in=reporte_ids, fecha=timezone.localdate()
        ).values_list("reporte_id", flat=True)
    )


def reportes_propios(usuario, reporte_ids: list[int]) -> set[int]:
    return set(
        ReportePrecio.objects.filter(autor=usuario, pk__in=reporte_ids).values_list("pk", flat=True)
    )


def ultimo_establecimiento_id(usuario) -> int | None:
    """La tienda donde la persona registró por última vez (solo suya, solo si sigue activa).

    Sirve para dejarla elegida al registrar el siguiente precio: quien recorre un local suele
    reportar varios productos seguidos. No expone nada de otras personas (M-15).
    """
    return (
        ReportePrecio.objects.filter(autor=usuario, establecimiento__activo=True)
        .order_by("-creado_en", "-pk")
        .values_list("establecimiento_id", flat=True)
        .first()
    )


def productos_para_registrar(limite: int = 8) -> list:
    """Productos a un toque al registrar: los más reportados primero, luego por nombre.

    Solo productos públicos con alguna presentación registrable. Sin criterio comercial: el orden
    es por actividad de la comunidad, igual que los destacados de la portada.
    """
    presentaciones = catalogo.presentaciones_publicas().filter(producto=OuterRef("pk"))
    return list(
        catalogo.con_fotos(catalogo.productos_publicos())
        .filter(Exists(presentaciones))
        .annotate(
            n_reportes=Count(
                "presentaciones__reportes",
                filter=Q(presentaciones__reportes__estado=ReportePrecio.Estado.PUBLICADO),
                distinct=True,
            )
        )
        .order_by("-n_reportes", "nombre")[:limite]
    )
