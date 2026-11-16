"""Lecturas del módulo precios (capa de aplicación).

`politica_vigencia` traduce la configuración (settings.PRECIOS, ADR-0003) a la política de
dominio. Vive aquí para que servicios de escritura y selectores de otros módulos usen la misma.
"""

from django.conf import settings

from .domain.vigencia import PoliticaVigencia
from .models import ReportePrecio


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
        .select_related("presentacion__producto", "establecimiento")
        .order_by("-creado_en")
    )
