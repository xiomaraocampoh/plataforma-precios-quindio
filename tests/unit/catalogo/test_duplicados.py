"""PU-05 · RF-06 · D-05: normalización de nombres y detección de posibles duplicados."""

import pytest

from apps.catalogo.domain.duplicados import normalizar_nombre, son_posibles_duplicados

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("nombre", "esperado"),
    [
        ("Arroz Diana", "arroz diana"),
        ("arroz DIANA", "arroz diana"),
        ("Café Águila Roja", "cafe aguila roja"),
        ("Piña", "piña"),
        ("PIÑA Golden", "piña golden"),
        ("  Arroz,   Diana. ", "arroz diana"),
        ("Coca-Cola!", "coca cola"),
    ],
)
def test_normalizar_nombre(nombre, esperado):
    # D-05: minúsculas, sin tildes salvo la ñ, sin puntuación ni espacios dobles
    assert normalizar_nombre(nombre) == esperado


def test_mayusculas_distintas_son_el_mismo_nombre():
    assert normalizar_nombre("Arroz Diana") == normalizar_nombre("arroz DIANA")


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("Arroz Diana", "arroz DIANA"),
        ("Café Águila Roja", "cafe aguila roja"),
        ("Aceite Premier", "Aceite Premir"),
    ],
)
def test_nombres_similares_son_posibles_duplicados(a, b):
    assert son_posibles_duplicados(a, b)


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("Arroz Diana", "Arroz Roa"),
        ("Leche entera", "Leche deslactosada"),
    ],
)
def test_nombres_distintos_no_son_duplicados(a, b):
    assert not son_posibles_duplicados(a, b)


def test_umbral_es_parametrizable():
    # Con un umbral más permisivo, marcas distintas del mismo producto se señalan.
    assert son_posibles_duplicados("Arroz Diana", "Arroz Roa", umbral=0.6)
    # Con un umbral exigente, un error de digitación ya no basta.
    assert not son_posibles_duplicados("Aceite Premier", "Aceite Premir", umbral=0.99)


def test_nombres_vacios_no_son_duplicados():
    # Sin texto no hay base de comparación; no se marca nada para el moderador.
    assert not son_posibles_duplicados("", "   ")
    assert not son_posibles_duplicados("...", "Arroz")


@pytest.mark.parametrize("umbral", [-0.1, 1.5])
def test_umbral_fuera_de_rango_es_rechazado(umbral):
    with pytest.raises(ValueError):
        son_posibles_duplicados("Arroz", "Arroz", umbral=umbral)
