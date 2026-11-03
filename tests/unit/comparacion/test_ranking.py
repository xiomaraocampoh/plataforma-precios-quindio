"""Neutralidad de la comparación (EC-06 / M-06: objetivo y mínimo 100 %)."""

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from apps.comparacion.domain.ranking import ResultadoComparacion, ordenar_neutral

pytestmark = pytest.mark.unit


def _r(eid: int, nombre: str, unitario: str, promo: bool = False) -> ResultadoComparacion:
    return ResultadoComparacion(
        establecimiento_id=eid,
        establecimiento=nombre,
        presentacion="Arroz 1 kg",
        precio=Decimal(unitario),
        precio_unitario=Decimal(unitario),
        unidad_base="kg",
        fuente="reportante",
        confianza="media",
        fecha_observacion=datetime(2026, 11, 1, tzinfo=UTC),
        es_promocion=promo,
    )


def test_ordena_por_menor_precio_unitario():
    datos = [_r(1, "Súper A", "5200"), _r(2, "Tienda B", "4800"), _r(3, "Mini C", "5000")]
    assert [r.establecimiento_id for r in ordenar_neutral(datos)] == [2, 3, 1]


def test_empate_se_resuelve_por_nombre_sin_importar_mayusculas():
    datos = [_r(1, "zeta", "5000"), _r(2, "Alfa", "5000")]
    assert [r.establecimiento for r in ordenar_neutral(datos)] == ["Alfa", "zeta"]


def test_marcar_promocion_no_altera_el_orden():
    datos = [_r(1, "Súper A", "5200"), _r(2, "Tienda B", "4800"), _r(3, "Mini C", "5000")]
    con_promo = [replace(d, es_promocion=(d.establecimiento_id == 1)) for d in datos]
    orden_sin = [r.establecimiento_id for r in ordenar_neutral(datos)]
    orden_con = [r.establecimiento_id for r in ordenar_neutral(con_promo)]
    assert orden_sin == orden_con


def test_resultado_promocional_queda_distinguido():
    resultado = ordenar_neutral([_r(1, "Súper A", "5200", promo=True)])[0]
    assert resultado.es_promocion is True
