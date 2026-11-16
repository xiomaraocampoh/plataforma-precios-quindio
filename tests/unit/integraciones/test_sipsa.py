"""RF-07: interpretación de los valores del CSV de SIPSA (DANE) descargado a mano."""

from datetime import date
from decimal import Decimal

import pytest

from apps.integraciones.domain.sipsa import interpretar_fecha, interpretar_precio_cop

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("4500", Decimal("4500")),
        ("4.500", Decimal("4500")),  # punto de miles (es-CO)
        ("12.345.678", Decimal("12345678")),
        ("4.500,50", Decimal("4500.50")),  # coma decimal
        ("$ 4.500", Decimal("4500")),
        (" 3200,5 ", Decimal("3200.5")),
        ("4500.75", Decimal("4500.75")),  # punto decimal si no agrupa de a tres
    ],
)
def test_interpretar_precio_cop(texto, esperado):
    assert interpretar_precio_cop(texto) == esperado


@pytest.mark.parametrize("texto", ["", "n.d.", "0", "-4.500", "4,500,00"])
def test_precio_vacio_cero_negativo_o_mal_formado_se_rechaza(texto):
    with pytest.raises(ValueError):
        interpretar_precio_cop(texto)


@pytest.mark.parametrize("texto", ["2026-11-14", "14/11/2026", " 14/11/2026 "])
def test_interpretar_fecha_en_formato_iso_o_dia_mes_anio(texto):
    assert interpretar_fecha(texto) == date(2026, 11, 14)


@pytest.mark.parametrize("texto", ["", "11/14/2026", "2026-13-01", "ayer"])
def test_fecha_invalida_se_rechaza(texto):
    with pytest.raises(ValueError):
        interpretar_fecha(texto)
