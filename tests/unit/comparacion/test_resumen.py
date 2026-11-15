"""Resumen de una comparación: rango de precios y diferencia (M-05, EC-06). Python puro."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from apps.comparacion.domain.ranking import ResultadoComparacion
from apps.comparacion.domain.resumen import resumir_precios

pytestmark = pytest.mark.unit


def _r(eid: int, unitario: str, base: str = "kg") -> ResultadoComparacion:
    return ResultadoComparacion(
        establecimiento_id=eid,
        establecimiento=f"Tienda {eid}",
        presentacion="Arroz 1 kg",
        precio=Decimal(unitario),
        precio_unitario=Decimal(unitario),
        unidad_base=base,
        fuente="reportante",
        confianza="media",
        fecha_observacion=datetime(2026, 11, 1, tzinfo=UTC),
    )


def test_sin_resultados_no_hay_resumen():
    r = resumir_precios([])
    assert r.cantidad == 0
    assert r.minimo_unitario is None
    assert r.diferencia_pct is None


def test_un_solo_resultado_no_tiene_diferencia():
    r = resumir_precios([_r(1, "5000")])
    assert r.cantidad == 1
    assert r.minimo_unitario == Decimal("5000")
    assert r.diferencia_pct is None


def test_diferencia_porcentual_sobre_el_mas_caro():
    r = resumir_precios([_r(1, "4800"), _r(2, "5200")])
    assert (r.minimo_unitario, r.maximo_unitario) == (Decimal("4800"), Decimal("5200"))
    assert r.diferencia_pct == 8  # (5200-4800)/5200 = 7,69 % → 8


def test_precios_iguales_diferencia_cero():
    assert resumir_precios([_r(1, "5000"), _r(2, "5000")]).diferencia_pct == 0


def test_unidades_base_distintas_no_se_comparan():
    r = resumir_precios([_r(1, "5000", "kg"), _r(2, "3000", "L")])
    assert r.cantidad == 2
    assert r.unidad_base is None
    assert r.diferencia_pct is None


def test_maximo_cero_no_divide():
    assert resumir_precios([_r(1, "0"), _r(2, "0")]).diferencia_pct == 0
