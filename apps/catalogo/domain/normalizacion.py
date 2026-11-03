"""Normalización de precios por unidad de medida (M-05, EC-06).

Capa de dominio: Python puro, sin Django. Se desarrolla con TDD.
"""

from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum


class Unidad(StrEnum):
    GRAMO = "g"
    KILOGRAMO = "kg"
    MILILITRO = "ml"
    LITRO = "L"
    UNIDAD = "und"


# unidad → (unidad base de comparación, factor de conversión a la base)
_CONVERSION: dict[Unidad, tuple[Unidad, Decimal]] = {
    Unidad.GRAMO: (Unidad.KILOGRAMO, Decimal("0.001")),
    Unidad.KILOGRAMO: (Unidad.KILOGRAMO, Decimal("1")),
    Unidad.MILILITRO: (Unidad.LITRO, Decimal("0.001")),
    Unidad.LITRO: (Unidad.LITRO, Decimal("1")),
    Unidad.UNIDAD: (Unidad.UNIDAD, Decimal("1")),
}

CENTAVOS = Decimal("0.01")


class UnidadIncompatibleError(ValueError):
    """Se intentó comparar presentaciones con magnitudes distintas (p. ej. kg vs L)."""


def a_unidad_base(cantidad: Decimal, unidad: Unidad | str) -> tuple[Decimal, Unidad]:
    if cantidad <= 0:
        raise ValueError("La cantidad de la presentación debe ser positiva.")
    base, factor = _CONVERSION[Unidad(unidad)]
    return cantidad * factor, base


def precio_por_unidad(
    precio: Decimal, cantidad: Decimal, unidad: Unidad | str
) -> tuple[Decimal, Unidad]:
    """Devuelve el precio por unidad base ($/kg, $/L o $/und), redondeado a centavos."""
    if precio <= 0:
        raise ValueError("El precio debe ser positivo.")
    cantidad_base, base = a_unidad_base(cantidad, unidad)
    return (precio / cantidad_base).quantize(CENTAVOS, rounding=ROUND_HALF_UP), base


def son_comparables(u1: Unidad | str, u2: Unidad | str) -> bool:
    return _CONVERSION[Unidad(u1)][0] == _CONVERSION[Unidad(u2)][0]


def exigir_comparables(u1: Unidad | str, u2: Unidad | str) -> None:
    if not son_comparables(u1, u2):
        raise UnidadIncompatibleError(f"No se puede comparar {u1} con {u2}.")
