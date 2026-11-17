"""SIPSA por servicio web (promediosSipsaCiudad): limpieza y selección de lo reciente. TDD."""

from datetime import date
from decimal import Decimal

import pytest

from apps.integraciones.domain.sipsa import (
    RegistroCiudad,
    limpiar_nombre_sipsa,
    recientes_de_la_ciudad,
    registro_desde_campos,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("crudo", "limpio"),
    [
        ("Tomate*", "Tomate"),
        ("Piña *", "Piña"),
        ("  Limón Común ", "Limón Común"),
        ("Coco", "Coco"),
    ],
)
def test_limpia_los_asteriscos_del_dane(crudo, limpio):
    assert limpiar_nombre_sipsa(crudo) == limpio


def test_registro_desde_los_campos_del_xml():
    r = registro_desde_campos(
        {
            "ciudad": "ARMENIA",
            "producto": "Papa negra*",
            "precioPromedio": "3020",
            "fechaCaptura": "2026-11-12T00:00:00-05:00",
        }
    )
    assert r == RegistroCiudad("ARMENIA", "Papa negra", Decimal("3020"), date(2026, 11, 12))


@pytest.mark.parametrize(
    "campos",
    [
        {
            "ciudad": "ARMENIA",
            "producto": "Coco",
            "precioPromedio": "0",
            "fechaCaptura": "2026-11-12",
        },
        {
            "ciudad": "ARMENIA",
            "producto": "Coco",
            "precioPromedio": "x",
            "fechaCaptura": "2026-11-12",
        },
        {"ciudad": "ARMENIA", "producto": "", "precioPromedio": "10", "fechaCaptura": "2026-11-12"},
        {"ciudad": "ARMENIA", "producto": "Coco", "precioPromedio": "10", "fechaCaptura": "ayer"},
    ],
)
def test_un_registro_invalido_se_rechaza(campos):
    with pytest.raises(ValueError):
        registro_desde_campos(campos)


def _r(ciudad, producto, precio, dia):
    return RegistroCiudad(ciudad, producto, Decimal(precio), date(2026, 11, dia))


def test_solo_la_ciudad_pedida_y_los_ultimos_dias():
    registros = [
        _r("ARMENIA", "Coco", "3000", 1),
        _r("ARMENIA", "Coco", "3600", 12),
        _r("ARMENIA", "Lulo", "5200", 10),
        _r("PEREIRA", "Coco", "2900", 12),
        _r("Armenia", "Mora de Castilla", "7900", 12),
    ]
    elegidos = recientes_de_la_ciudad(registros, ciudad="armenia", dias=7)
    assert {(r.producto, r.fecha.day) for r in elegidos} == {
        ("Coco", 12),
        ("Lulo", 10),
        ("Mora de Castilla", 12),
    }


def test_un_dia_repetido_conserva_el_ultimo_registro():
    elegidos = recientes_de_la_ciudad(
        [_r("ARMENIA", "Coco", "3000", 12), _r("ARMENIA", "Coco", "3100", 12)],
        ciudad="ARMENIA",
        dias=7,
    )
    assert [r.precio for r in elegidos] == [Decimal("3100")]


def test_sin_registros_de_la_ciudad_no_hay_nada():
    assert recientes_de_la_ciudad([_r("CALI", "Coco", "1", 1)], ciudad="ARMENIA", dias=7) == []
