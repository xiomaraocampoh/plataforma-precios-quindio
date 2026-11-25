"""Precio oficial verificado frente a lo que reportan los usuarios (ADR-018). Python puro — TDD.

Si al menos 2 reportes de los últimos 7 días difieren más de 10 % del precio oficial, la
comparación muestra «Usuarios reportan $X» (el más reciente de ellos) y la confianza baja a media.
No toca el orden (EC-06).
"""

from collections.abc import Iterable
from datetime import datetime, timedelta
from decimal import Decimal

UMBRAL_DISCREPANCIA = Decimal("0.10")
MIN_REPORTES_DISCREPANTES = 2
DIAS_DISCREPANCIA = 7


def _difiere(oficial: Decimal, reportado: Decimal) -> bool:
    return abs(reportado - oficial) / oficial > UMBRAL_DISCREPANCIA


def discrepancia(
    oficial: Decimal, reportes: Iterable[tuple[Decimal, datetime]], ahora: datetime
) -> Decimal | None:
    """El precio reportado que se advierte junto al oficial, o None si no hay discrepancia.

    `reportes` son (precio, fecha de observación). Una fecha futura (reloj adelantado) cuenta como
    ahora.
    """
    if oficial <= 0:
        raise ValueError("El precio oficial debe ser positivo.")
    desde = ahora - timedelta(days=DIAS_DISCREPANCIA)
    discrepantes = [
        (min(fecha, ahora), precio)
        for precio, fecha in reportes
        if min(fecha, ahora) >= desde and _difiere(oficial, precio)
    ]
    if len(discrepantes) < MIN_REPORTES_DISCREPANTES:
        return None
    return max(discrepantes, key=lambda d: d[0])[1]
