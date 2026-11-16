"""Resumen de una comparación (rango de precios y diferencia). Python puro — TDD.

No altera el orden (EC-06): solo describe el conjunto ya ordenado por `ranking`.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from .ranking import ResultadoComparacion


@dataclass(frozen=True)
class ResumenComparacion:
    cantidad: int
    unidad_base: str | None  # None si las unidades base difieren (no son comparables)
    minimo_unitario: Decimal | None
    maximo_unitario: Decimal | None
    diferencia_pct: int | None  # (máx - mín) / máx, redondeado; None si no aplica


def resumir_precios(resultados: list[ResultadoComparacion]) -> ResumenComparacion:
    if not resultados:
        return ResumenComparacion(0, None, None, None, None)

    unidades = {r.unidad_base for r in resultados}
    unitarios = [r.precio_unitario for r in resultados]
    minimo, maximo = min(unitarios), max(unitarios)

    unidad = next(iter(unidades)) if len(unidades) == 1 else None
    diferencia = None
    if unidad is not None and len(resultados) > 1:
        if maximo == 0:
            diferencia = 0
        else:
            pct = (maximo - minimo) / maximo * 100
            diferencia = int(pct.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return ResumenComparacion(len(resultados), unidad, minimo, maximo, diferencia)
