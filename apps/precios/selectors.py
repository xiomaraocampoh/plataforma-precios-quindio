"""Lecturas del módulo precios (capa de aplicación).

`politica_vigencia` traduce la configuración (settings.PRECIOS, ADR-0003) a la política de
dominio. Vive aquí para que servicios de escritura y selectores de otros módulos usen la misma.
"""

from django.conf import settings

from .domain.vigencia import PoliticaVigencia


def politica_vigencia() -> PoliticaVigencia:
    p = settings.PRECIOS
    return PoliticaVigencia(
        dias_reporte=p["VIGENCIA_REPORTE_DIAS"],
        dias_perecedero=p["VIGENCIA_PERECEDERO_DIAS"],
        dias_oficial=p["VIGENCIA_OFICIAL_DIAS"],
    )
