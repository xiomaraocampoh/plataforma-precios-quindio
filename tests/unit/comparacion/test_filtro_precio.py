"""Filtro por rango de precio de la comparación. Solo reduce; nunca reordena (EC-06)."""

from dataclasses import dataclass
from decimal import Decimal

import pytest

from apps.comparacion.domain.filtros import FiltroPrecio, filtrar_por_precio

pytestmark = pytest.mark.unit


@dataclass(frozen=True)
class Fila:
    nombre: str
    precio: Decimal


FILAS = [  # ya vienen en orden neutral; hay un empate de precio a propósito
    Fila("Súper Central", Decimal("2300")),
    Fila("Tienda Granada", Decimal("2400")),
    Fila("Mini Calarcá", Decimal("2400")),
    Fila("Tienda Doña Rosa", Decimal("2600")),
]


def _precio(f: Fila) -> Decimal:
    return f.precio


def _nombres(filas: list[Fila]) -> list[str]:
    return [f.nombre for f in filas]


def test_sin_filtro_devuelve_todo_en_el_mismo_orden():
    assert filtrar_por_precio(FILAS, FiltroPrecio(), _precio) == FILAS


def test_minimo_y_maximo_son_inclusivos():
    filtro = FiltroPrecio(minimo=Decimal("2400"), maximo=Decimal("2600"))
    assert _nombres(filtrar_por_precio(FILAS, filtro, _precio)) == [
        "Tienda Granada",
        "Mini Calarcá",
        "Tienda Doña Rosa",
    ]


def test_solo_minimo():
    filtro = FiltroPrecio(minimo=Decimal("2500"))
    assert _nombres(filtrar_por_precio(FILAS, filtro, _precio)) == ["Tienda Doña Rosa"]


def test_solo_maximo():
    filtro = FiltroPrecio(maximo=Decimal("2300"))
    assert _nombres(filtrar_por_precio(FILAS, filtro, _precio)) == ["Súper Central"]


def test_un_rango_de_un_solo_valor_es_valido_y_conserva_el_orden_de_los_empates():
    filtro = FiltroPrecio(minimo=Decimal("2400"), maximo=Decimal("2400"))
    assert _nombres(filtrar_por_precio(FILAS, filtro, _precio)) == [
        "Tienda Granada",
        "Mini Calarcá",
    ]


def test_un_rango_sin_coincidencias_devuelve_lista_vacia():
    filtro = FiltroPrecio(minimo=Decimal("9000"))
    assert filtrar_por_precio(FILAS, filtro, _precio) == []


def test_el_resultado_es_siempre_una_subsecuencia_de_la_entrada():
    for filtro in [
        FiltroPrecio(minimo=Decimal("2400")),
        FiltroPrecio(maximo=Decimal("2400")),
        FiltroPrecio(minimo=Decimal("2300"), maximo=Decimal("2500")),
    ]:
        resultado = filtrar_por_precio(FILAS, filtro, _precio)
        posiciones = [FILAS.index(f) for f in resultado]
        assert posiciones == sorted(posiciones)  # mismo orden relativo, nada agregado


def test_filtro_activo():
    assert not FiltroPrecio().activo
    assert FiltroPrecio(minimo=Decimal("1")).activo
    assert FiltroPrecio(maximo=Decimal("1")).activo


def test_minimo_mayor_que_maximo_es_un_error():
    with pytest.raises(ValueError, match="mínimo"):
        FiltroPrecio(minimo=Decimal("3000"), maximo=Decimal("2000"))


@pytest.mark.parametrize("campo", ["minimo", "maximo"])
def test_los_montos_negativos_son_un_error(campo):
    with pytest.raises(ValueError, match="negativ"):
        FiltroPrecio(**{campo: Decimal("-1")})
