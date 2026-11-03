"""Orden neutral de la comparación (EC-06, M-06). Python puro — TDD.

Regla ética de la guía: el orden responde SOLO al criterio declarado al usuario.
Ningún atributo comercial (promoción, perfil de comercio, patrocinio) entra en la clave.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

CRITERIO_DECLARADO = "Menor precio por unidad de medida; empate: nombre del establecimiento."


@dataclass(frozen=True)
class ResultadoComparacion:
    establecimiento_id: int
    establecimiento: str
    presentacion: str
    precio: Decimal
    precio_unitario: Decimal
    unidad_base: str
    fuente: str
    confianza: str
    fecha_observacion: datetime
    es_promocion: bool = False  # se muestra como etiqueta, nunca altera el orden


def _clave_neutral(r: ResultadoComparacion) -> tuple:
    return (r.precio_unitario, r.establecimiento.casefold(), r.establecimiento_id)


def ordenar_neutral(resultados: list[ResultadoComparacion]) -> list[ResultadoComparacion]:
    return sorted(resultados, key=_clave_neutral)
