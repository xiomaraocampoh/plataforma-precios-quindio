"""RF-19: filtros por municipio y barrio. Solo reducen resultados; nunca reordenan (EC-06)."""

from dataclasses import dataclass

import pytest

from apps.comparacion.domain.filtros import FiltroUbicacion, filtrar

pytestmark = pytest.mark.unit


@dataclass(frozen=True)
class Fila:
    nombre: str
    municipio: str
    barrio: str


FILAS = [  # ya vienen en orden neutral
    Fila("Súper Central", "Armenia", "Centro"),
    Fila("Tienda Granada", "Armenia", "Granada"),
    Fila("Mini Calarcá", "Calarcá", "Centro"),
    Fila("Tienda Doña Rosa", "Armenia", "Centro"),
]


def _ubicacion(f: Fila) -> tuple[str, str]:
    return f.municipio, f.barrio


def test_sin_filtro_devuelve_todo_en_el_mismo_orden():
    assert filtrar(FILAS, FiltroUbicacion(), _ubicacion) == FILAS


def test_filtra_por_municipio_y_conserva_el_orden_neutral():
    assert [f.nombre for f in filtrar(FILAS, FiltroUbicacion(municipio="Armenia"), _ubicacion)] == [
        "Súper Central",
        "Tienda Granada",
        "Tienda Doña Rosa",
    ]


def test_filtra_por_municipio_y_barrio():
    filtro = FiltroUbicacion(municipio="Armenia", barrio="Centro")
    assert [f.nombre for f in filtrar(FILAS, filtro, _ubicacion)] == [
        "Súper Central",
        "Tienda Doña Rosa",
    ]


def test_ignora_mayusculas_tildes_y_espacios():
    filtro = FiltroUbicacion(municipio="  CALARCA ", barrio="centro")
    assert [f.nombre for f in filtrar(FILAS, filtro, _ubicacion)] == ["Mini Calarcá"]


def test_el_resultado_es_siempre_una_subsecuencia_de_la_entrada():
    for filtro in [FiltroUbicacion(barrio="Centro"), FiltroUbicacion(municipio="Pereira")]:
        resultado = filtrar(FILAS, filtro, _ubicacion)
        posiciones = [FILAS.index(f) for f in resultado]
        assert posiciones == sorted(posiciones)  # mismo orden relativo, nada agregado


def test_filtro_activo():
    assert not FiltroUbicacion().activo
    assert FiltroUbicacion(barrio="Centro").activo
