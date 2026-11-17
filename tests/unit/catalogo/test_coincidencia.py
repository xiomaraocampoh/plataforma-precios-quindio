"""puntuar_coincidencia: qué tanto se parece un producto del catálogo a la pista de una foto."""

from decimal import Decimal

import pytest

from apps.catalogo.domain.coincidencia import (
    UMBRAL_CANDIDATO,
    palabras_significativas,
    puntuar_coincidencia,
)

pytestmark = pytest.mark.unit

KG = [(Decimal("1"), "kg"), (Decimal("500"), "g")]


def _p(nombre, marca, producto, producto_marca, cantidad="", unidad="", presentaciones=()):
    return puntuar_coincidencia(
        nombre, marca, cantidad, unidad, producto, producto_marca, list(presentaciones)
    )


def test_palabras_vacias_y_tildes_se_ignoran():
    assert palabras_significativas("Pasta de Spaghetti x 500 con Huevo") == [
        "spaghetti",
        "500",
        "huevo",
    ]
    assert palabras_significativas("Café") == ["cafe"]


def test_misma_marca_y_nombre_parcial_supera_el_umbral():
    assert _p("Arroz blanco", "Diana", "Arroz blanco premium", "Diana") > UMBRAL_CANDIDATO


def test_la_marca_correcta_puntua_mas_que_otra_marca():
    diana = _p("Arroz blanco", "Diana", "Arroz blanco premium", "Diana")
    roa = _p("Arroz blanco", "Diana", "Arroz blanco", "Roa")
    assert diana > roa


def test_marca_muy_parecida_cuenta_como_marca():
    assert _p("Café molido", "Sello Rojo", "Café molido", "Sello  rojo.") == pytest.approx(
        _p("Café molido", "Sello Rojo", "Café molido", "Sello Rojo")
    )


def test_nombre_generico_de_la_ia():
    assert _p("Pasta spaghetti", "Doria", "Spaghetti", "Doria") > UMBRAL_CANDIDATO


def test_la_presentacion_igual_da_un_bono():
    con = _p("Arroz", "Roa", "Arroz blanco", "Roa", "500", "g", KG)
    sin = _p("Arroz", "Roa", "Arroz blanco", "Roa", "250", "g", KG)
    assert con > sin


def test_cantidad_invalida_o_vacia_no_rompe():
    assert _p("Arroz", "", "Arroz blanco", "Roa", "medio", "kilo", KG) >= 0
    assert _p("Arroz", "", "Arroz blanco", "Roa", "0", "g", KG) >= 0


def test_sin_marca_en_la_pista_el_nombre_basta():
    assert _p("Spaghetti", "", "Spaghetti", "Doria") > UMBRAL_CANDIDATO


def test_nada_parecido_queda_bajo_el_umbral():
    assert _p("Zapatos deportivos", "Nike", "Spaghetti", "Doria") < UMBRAL_CANDIDATO
    assert _p("", "", "Spaghetti", "Doria") == 0


def test_solo_la_marca_sin_el_tipo_de_producto_no_basta():
    assert _p("Detergente", "Diana", "Arroz blanco premium", "Diana") < UMBRAL_CANDIDATO
