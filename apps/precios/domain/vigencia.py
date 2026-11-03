"""Vigencia de un precio (EC-02, D-02). Python puro — TDD.

Decisión provisional (ADR-0003): reportado 7 días, perecedero 3 días,
oficial de comercio 30 días sin confirmar.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum


class Fuente(StrEnum):
    REPORTANTE = "reportante"
    COMERCIO = "comercio"
    SIPSA = "sipsa"


@dataclass(frozen=True)
class PoliticaVigencia:
    dias_reporte: int = 7
    dias_perecedero: int = 3
    dias_oficial: int = 30


def ventana_vigencia(fuente: Fuente, *, perecedero: bool, politica: PoliticaVigencia) -> timedelta:
    if fuente == Fuente.COMERCIO:
        return timedelta(days=politica.dias_oficial)
    if perecedero:
        return timedelta(days=politica.dias_perecedero)
    return timedelta(days=politica.dias_reporte)


def es_vigente(
    fecha_observacion: datetime,
    ahora: datetime,
    fuente: Fuente = Fuente.REPORTANTE,
    *,
    perecedero: bool = False,
    politica: PoliticaVigencia | None = None,
) -> bool:
    politica = politica or PoliticaVigencia()
    if fecha_observacion > ahora:
        raise ValueError("La fecha de observación no puede estar en el futuro.")
    return ahora - fecha_observacion <= ventana_vigencia(
        fuente, perecedero=perecedero, politica=politica
    )
