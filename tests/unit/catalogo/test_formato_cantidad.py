"""Formato legible de la cantidad de una presentación (M-02: evitar «5E+2 g»)."""

from decimal import Decimal

import pytest

from apps.catalogo.domain.normalizacion import formatear_cantidad

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("cantidad", "esperado"),
    [
        (Decimal("500.000"), "500"),  # antes: Decimal.normalize() → «5E+2»
        (Decimal("30"), "30"),
        (Decimal("1.000"), "1"),
        (Decimal("2.500"), "2,5"),  # coma decimal (es-CO)
        (Decimal("0.250"), "0,25"),
        (Decimal("1000"), "1000"),
        (Decimal("12.345"), "12,345"),
    ],
)
def test_formatear_cantidad_sin_notacion_cientifica(cantidad, esperado):
    assert formatear_cantidad(cantidad) == esperado


@pytest.mark.parametrize("cantidad", [Decimal("0"), Decimal("-1")])
def test_formatear_cantidad_rechaza_valores_no_positivos(cantidad):
    with pytest.raises(ValueError):
        formatear_cantidad(cantidad)
