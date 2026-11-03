"""Credibilidad del dato (EC-03, M-11, M-12, D-03). Python puro — TDD.

Heurística inicial deliberadamente simple; el equipo la calibra con el
conjunto de prueba sembrado de reportes anómalos (ver docs/calidad).
"""

from decimal import Decimal
from enum import StrEnum
from statistics import median

from .vigencia import Fuente

MIN_MUESTRAS_PARA_ANOMALIA = 3


class NivelConfianza(StrEnum):
    ALTA = "alta"
    MEDIA = "media"
    BAJA = "baja"


def es_anomalo(precio: Decimal, referencia: list[Decimal], tolerancia: Decimal) -> bool:
    """Un precio es anómalo si se aleja de la mediana reciente más que la tolerancia relativa."""
    if len(referencia) < MIN_MUESTRAS_PARA_ANOMALIA:
        return False  # sin suficiente evidencia no se castiga al reportante (M-12)
    mediana = Decimal(median(referencia))
    if mediana == 0:
        return False
    return abs(precio - mediana) / mediana > tolerancia


def nivel_confianza(fuente: Fuente, confirmaciones: int, anomalo: bool) -> NivelConfianza:
    if anomalo:
        return NivelConfianza.BAJA
    if fuente == Fuente.COMERCIO or confirmaciones >= 2:
        return NivelConfianza.ALTA
    return NivelConfianza.MEDIA
