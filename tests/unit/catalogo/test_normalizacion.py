from decimal import Decimal

import pytest

from apps.catalogo.domain.normalizacion import (
    Unidad,
    UnidadIncompatibleError,
    exigir_comparables,
    precio_por_unidad,
    son_comparables,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("precio", "cantidad", "unidad", "esperado", "base"),
    [
        (Decimal("4500"), Decimal("500"), Unidad.GRAMO, Decimal("9000.00"), Unidad.KILOGRAMO),
        (Decimal("8200"), Decimal("1"), Unidad.KILOGRAMO, Decimal("8200.00"), Unidad.KILOGRAMO),
        (Decimal("3900"), Decimal("900"), Unidad.MILILITRO, Decimal("4333.33"), Unidad.LITRO),
        (Decimal("12000"), Decimal("6"), Unidad.UNIDAD, Decimal("2000.00"), Unidad.UNIDAD),
    ],
)
def test_precio_por_unidad_normaliza_a_unidad_base(precio, cantidad, unidad, esperado, base):
    assert precio_por_unidad(precio, cantidad, unidad) == (esperado, base)


def test_presentacion_mas_grande_puede_ser_mas_barata_por_unidad():
    bolsa_500g, _ = precio_por_unidad(Decimal("4500"), Decimal("500"), "g")
    bolsa_1kg, _ = precio_por_unidad(Decimal("8200"), Decimal("1"), "kg")
    assert bolsa_1kg < bolsa_500g


@pytest.mark.parametrize("cantidad", [Decimal("0"), Decimal("-1")])
def test_cantidad_no_positiva_es_rechazada(cantidad):
    with pytest.raises(ValueError):
        precio_por_unidad(Decimal("1000"), cantidad, Unidad.GRAMO)


def test_precio_no_positivo_es_rechazado():
    with pytest.raises(ValueError):
        precio_por_unidad(Decimal("0"), Decimal("1"), Unidad.LITRO)


def test_gramos_y_kilos_son_comparables_pero_no_con_litros():
    assert son_comparables("g", "kg")
    assert not son_comparables("g", "L")
    with pytest.raises(UnidadIncompatibleError):
        exigir_comparables(Unidad.KILOGRAMO, Unidad.MILILITRO)
