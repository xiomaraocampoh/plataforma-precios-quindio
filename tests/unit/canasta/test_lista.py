"""Entender una lista de mercado escrita a mano: «2 kg arroz», «leche 1 L», «una docena de huevos»."""

from decimal import Decimal

import pytest

from apps.canasta.domain.lista import parsear_lista

pytestmark = pytest.mark.unit


def _uno(texto):
    lineas = parsear_lista(texto)
    assert len(lineas) == 1, lineas
    ln = lineas[0]
    return ln.producto, ln.cantidad, ln.unidad


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("2 kg arroz", ("arroz", Decimal("2"), "kg")),
        ("arroz 2kg", ("arroz", Decimal("2"), "kg")),
        ("1,5 kg de arroz", ("arroz", Decimal("1.5"), "kg")),
        ("1.5 kilos de arroz", ("arroz", Decimal("1.5"), "kg")),
        ("leche 1 L", ("leche", Decimal("1"), "L")),
        ("2 litros de leche", ("leche", Decimal("2"), "L")),
        ("500 g de azúcar", ("azúcar", Decimal("500"), "g")),
        ("500 gramos de azúcar", ("azúcar", Decimal("500"), "g")),
        ("250 ml de aceite", ("aceite", Decimal("250"), "ml")),
    ],
)
def test_cantidad_y_unidad_en_cualquier_lado(texto, esperado):
    assert _uno(texto) == esperado


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("2 libras de panela", ("panela", Decimal("1000"), "g")),
        ("1 libra de arroz", ("arroz", Decimal("500"), "g")),
        ("media libra de café", ("café", Decimal("250"), "g")),
        ("una docena de huevos", ("huevos", Decimal("12"), "und")),
        ("dos docenas de huevos", ("huevos", Decimal("24"), "und")),
        ("medio kilo de queso", ("queso", Decimal("0.5"), "kg")),
        ("un litro de leche", ("leche", Decimal("1"), "L")),
        ("tres panelas", ("panelas", Decimal("3"), None)),
    ],
)
def test_palabras_libras_y_docenas(texto, esperado):
    assert _uno(texto) == esperado


def test_sin_cantidad_queda_vacia_para_que_el_sistema_use_una_unidad():
    assert _uno("arroz") == ("arroz", None, None)


def test_cantidad_sin_unidad():
    assert _uno("3 huevos") == ("huevos", Decimal("3"), None)


def test_varias_lineas_viñetas_numeracion_y_comas():
    texto = "- arroz 2 kg\n* 1 L de leche\n1. huevos, panela; 3 tomates"
    assert [ln.producto for ln in parsear_lista(texto)] == [
        "arroz",
        "leche",
        "huevos",
        "panela",
        "tomates",
    ]


def test_la_coma_decimal_no_parte_la_linea():
    lineas = parsear_lista("1,5 kg arroz, 2 kg papa")
    assert [(ln.producto, ln.cantidad) for ln in lineas] == [
        ("arroz", Decimal("1.5")),
        ("papa", Decimal("2")),
    ]


def test_ignora_lineas_vacias_y_sin_letras():
    assert parsear_lista("\n  \n---\n123\n") == []


def test_cantidad_absurda_o_cero_no_se_inventa():
    ln = parsear_lista("0 kg arroz")[0]
    assert ln.cantidad is None  # 0 no es una cantidad: el sistema pregunta o usa el valor por defecto


def test_limita_la_cantidad_de_lineas():
    texto = "\n".join(f"producto{n}" for n in range(100))
    assert len(parsear_lista(texto)) <= 40


def test_normaliza_mayusculas_y_espacios():
    assert _uno("  2  KG   Arroz  Blanco ") == ("arroz blanco", Decimal("2"), "kg")
