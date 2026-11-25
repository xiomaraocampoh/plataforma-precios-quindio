"""Registro de extensiones de core (ADR-012, DP-1 opción B).

core guarda las extensiones por nombre de punto sin conocer a ninguna: así comparacion nunca
importa comercios y el contrato comercios-no-adelantado se conserva.
"""

import pytest

from core import extensiones

pytestmark = pytest.mark.unit

PUNTO = "prueba.punto"


@pytest.fixture(autouse=True)
def _aislar():
    antes = extensiones.extensiones(PUNTO)
    for e in antes:
        extensiones.retirar(PUNTO, e)
    yield
    for e in extensiones.extensiones(PUNTO):
        extensiones.retirar(PUNTO, e)


def test_un_punto_sin_registros_no_tiene_extensiones():
    assert extensiones.extensiones("punto.que.nadie.usa") == ()


def test_registrar_agrega_en_orden():
    a, b = object(), object()
    extensiones.registrar(PUNTO, a)
    extensiones.registrar(PUNTO, b)
    assert extensiones.extensiones(PUNTO) == (a, b)


def test_registrar_dos_veces_la_misma_no_la_duplica():
    # AppConfig.ready() puede correr más de una vez (pruebas, recarga del servidor)
    a = object()
    extensiones.registrar(PUNTO, a)
    extensiones.registrar(PUNTO, a)
    assert extensiones.extensiones(PUNTO) == (a,)


def test_retirar_quita_solo_esa_extension():
    a, b = object(), object()
    extensiones.registrar(PUNTO, a)
    extensiones.registrar(PUNTO, b)
    extensiones.retirar(PUNTO, a)
    assert extensiones.extensiones(PUNTO) == (b,)


def test_retirar_una_que_no_estaba_no_falla():
    extensiones.retirar(PUNTO, object())
    assert extensiones.extensiones(PUNTO) == ()


def test_lo_devuelto_es_una_copia_inmutable():
    a = object()
    extensiones.registrar(PUNTO, a)
    lista = extensiones.extensiones(PUNTO)
    assert isinstance(lista, tuple)


@pytest.mark.parametrize("punto", ["", "   "])
def test_el_punto_no_puede_estar_vacio(punto):
    with pytest.raises(ValueError):
        extensiones.registrar(punto, object())
