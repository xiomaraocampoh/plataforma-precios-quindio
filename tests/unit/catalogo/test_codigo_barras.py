"""RF-04: lectura de códigos de barras (GTIN) por escáner o cámara."""

import pytest

from apps.catalogo.domain.codigo_barras import es_gtin_valido, normalizar_codigo

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("crudo", "esperado"),
    [
        ("4006381333931", "4006381333931"),
        ("  4006381333931\n", "4006381333931"),
        ("4006 3813 33931", "4006381333931"),
        ("4006-3813-33931", "4006381333931"),
        ("", ""),
        ("abc", ""),
    ],
)
def test_normalizar_codigo_deja_solo_digitos(crudo, esperado):
    assert normalizar_codigo(crudo) == esperado


@pytest.mark.parametrize(
    "codigo",
    [
        "96385074",  # EAN-8
        "036000291452",  # UPC-A
        "4006381333931",  # EAN-13
        "10012345678902",  # GTIN-14
    ],
)
def test_gtin_valido(codigo):
    assert es_gtin_valido(codigo)


@pytest.mark.parametrize(
    "codigo",
    [
        "96385075",  # dígito de control erróneo
        "4006381333932",
        "123456789",  # longitud 9: no es un GTIN
        "1234567890",  # longitud 10
        "123456789012345",  # 15 dígitos
        "",
        "abcdefgh",
        "4006381333 931",  # espacio: debe normalizarse antes
        "0000000000000",  # ceros: control correcto pero no es un código real
    ],
)
def test_gtin_invalido(codigo):
    assert not es_gtin_valido(codigo)
