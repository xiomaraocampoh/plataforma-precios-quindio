"""Interpretar el monto que escribe una persona en el filtro de precio (formato colombiano)."""

from decimal import Decimal

import pytest

from apps.comparacion.domain.filtros import interpretar_monto

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("2500", Decimal("2500")),
        ("2.500", Decimal("2500")),  # el punto agrupa miles: así se escribe en Colombia
        ("$2.500", Decimal("2500")),
        ("  $ 2.500  ", Decimal("2500")),
        ("1.234.567", Decimal("1234567")),
        ("2.500,50", Decimal("2500.50")),  # la coma separa los decimales
        ("2500,5", Decimal("2500.5")),
        ("2500.50", Decimal("2500.50")),  # un punto con dos decimales no es de miles
        ("0", Decimal("0")),
    ],
)
def test_montos_validos(texto, esperado):
    assert interpretar_monto(texto) == esperado


@pytest.mark.parametrize("texto", ["", "   ", "$"])
def test_un_campo_vacio_significa_sin_limite(texto):
    assert interpretar_monto(texto) is None


@pytest.mark.parametrize("texto", ["abc", "-5", "1e3", "2,5,3", "12..5", "2.5.0", "1 000", "NaN"])
def test_los_montos_invalidos_son_un_error(texto):
    with pytest.raises(ValueError, match="monto"):
        interpretar_monto(texto)
