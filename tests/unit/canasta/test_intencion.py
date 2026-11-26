"""Qué quiere la persona en cada mensaje del chat: una lista nueva o un ajuste (sin IA)."""

import pytest

from apps.canasta.domain.intencion import Tipo, detectar_intencion

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "texto",
    ["empezar de nuevo", "Nueva lista", "borrar todo", "vaciar la canasta", "reiniciar"],
)
def test_reiniciar(texto):
    assert detectar_intencion(texto).tipo is Tipo.REINICIAR


@pytest.mark.parametrize("texto", ["menor total", "ordénalo por el más barato", "Más barato"])
def test_ordenar_por_total(texto):
    assert detectar_intencion(texto).tipo is Tipo.ORDENAR_TOTAL


@pytest.mark.parametrize("texto", ["más productos disponibles", "que tenga todo"])
def test_ordenar_por_cobertura(texto):
    assert detectar_intencion(texto).tipo is Tipo.ORDENAR_COBERTURA


def test_agregar_conserva_el_resto_del_mensaje():
    i = detectar_intencion("Agrega 2 kg de papa y una cebolla")
    assert i.tipo is Tipo.AGREGAR and i.resto == "2 kg de papa y una cebolla"
    assert detectar_intencion("también leche, huevos").tipo is Tipo.AGREGAR


def test_quitar_conserva_el_producto():
    i = detectar_intencion("quita la leche")
    assert i.tipo is Tipo.QUITAR and i.resto == "la leche"


def test_una_lista_es_una_lista_aunque_mencione_barato():
    texto = "2 kg arroz\n1 L leche más barata\nhuevos"
    assert detectar_intencion(texto).tipo is Tipo.LISTA


def test_lo_demas_es_una_lista():
    i = detectar_intencion("2 kg arroz, 1 L leche")
    assert i.tipo is Tipo.LISTA and i.resto == "2 kg arroz, 1 L leche"


def test_texto_vacio_es_una_lista_vacia():
    assert detectar_intencion("   ").tipo is Tipo.LISTA


@pytest.mark.parametrize(
    "texto",
    [
        "quita el arroz y ordénalo por menor total",
        "agrega leche y que tenga todo",
        "empezar de nuevo pero con menos productos y más barato",
    ],
)
def test_una_frase_compuesta_no_es_una_orden_corta(texto):
    # Una orden corta no se traga una frase con varias peticiones: la entiende la IA (o el sistema)
    assert detectar_intencion(texto).tipo in (Tipo.LISTA, Tipo.QUITAR, Tipo.AGREGAR)
    assert detectar_intencion(texto).tipo not in (
        Tipo.ORDENAR_TOTAL,
        Tipo.ORDENAR_COBERTURA,
        Tipo.REINICIAR,
    )


@pytest.mark.parametrize(
    "texto",
    [
        "¿Cómo registro un precio?",
        "como creo una cuenta",
        "ayuda",
        "necesito ayuda",
        "primeros pasos",
        "no entiendo cómo funciona",
        "dónde veo mis aportes",
        "qué es AhorraPues",
        "¿Para qué sirve esto?",
        "explícame cómo comparar",
        "qué puedes hacer",
    ],
)
def test_pedir_ayuda_es_una_pregunta_sobre_la_app(texto):
    assert detectar_intencion(texto).tipo is Tipo.AYUDA


@pytest.mark.parametrize(
    "texto",
    ["2 kg arroz, 1 L leche", "arroz", "arroz\nleche\nhuevos", "agrega leche", "menor total"],
)
def test_una_lista_o_una_orden_no_es_ayuda(texto):
    assert detectar_intencion(texto).tipo is not Tipo.AYUDA
