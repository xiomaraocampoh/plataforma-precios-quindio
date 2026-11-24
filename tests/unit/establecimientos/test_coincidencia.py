"""¿El establecimiento impreso en la etiqueta es uno del directorio? (ADR-0026). Dominio puro.

Solo se propone una tienda si la coincidencia es única: ante la duda se usa la última tienda de la
persona y ella decide. Nunca se crea una tienda por lo que diga una etiqueta.
"""

import pytest

from apps.establecimientos.domain.coincidencia import elegir_establecimiento

pytestmark = pytest.mark.unit

DIRECTORIO = [
    (1, "Supermercado La 14 Calima"),
    (2, "D1 Centro"),
    (3, "D1 Norte"),
    (4, "Tienda Doña Rosa"),
    (5, "Mercacentro Armenia"),
]


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("Tienda Doña Rosa", 4),
        ("TIENDA DOÑA ROSA", 4),
        ("Tienda Dona Rosa", 4),  # una lectura con un error menor (similitud D-05 ≥ 0,85)
        ("Mercacentro", 5),
        ("MERCACENTRO ARMENIA - Precio al público", 5),
        ("La 14 Calima", 1),
        ("Supermercado La 14 Calima", 1),
        ("D1 Centro", 2),
    ],
)
def test_coincidencia_unica(texto, esperado):
    assert elegir_establecimiento(texto, DIRECTORIO) == esperado


def test_coincidencia_ambigua_no_propone_ninguna():
    assert elegir_establecimiento("D1", DIRECTORIO) is None


@pytest.mark.parametrize("texto", ["", "  ", "a", "Éxito", "Precio", None])
def test_sin_texto_o_sin_coincidencia_no_propone(texto):
    assert elegir_establecimiento(texto, DIRECTORIO) is None


def test_directorio_vacio():
    assert elegir_establecimiento("D1 Centro", []) is None


def test_una_palabra_suelta_no_basta_dentro_de_otra():
    # «Rosa» no debe elegir «Tienda Doña Rosa» si el texto es «Rosado»
    assert elegir_establecimiento("Rosado", DIRECTORIO) is None


def test_la_igualdad_exacta_desempata():
    directorio = [(1, "Olímpica"), (2, "Olímpica Plaza")]
    assert elegir_establecimiento("Olímpica", directorio) == 1
