"""Reglas de la foto de un producto: qué se acepta y cómo se recorta (RF-06, M-03, EC-01).

Dominio puro, sin Django ni Pillow: solo decide si una subida es válida y qué región se recorta
para dejarla cuadrada. El procesamiento de la imagen vive aparte.
"""

import pytest

from apps.catalogo.domain.fotos import (
    LADO_MINIATURA,
    MAX_BYTES_SUBIDA,
    MAX_PIXELES,
    MIN_LADO,
    FotoInvalidaError,
    recorte_cuadrado,
    validar_subida,
)

pytestmark = pytest.mark.unit


def _valida(**cambios):
    datos = {"formato": "JPEG", "ancho": 800, "alto": 600, "tamano": 200_000}
    return validar_subida(**{**datos, **cambios})


# ───────────── Qué se acepta ─────────────


@pytest.mark.parametrize("formato", ["JPEG", "PNG", "WEBP"])
def test_acepta_jpg_png_y_webp(formato):
    _valida(formato=formato)  # no lanza


@pytest.mark.parametrize("formato", ["GIF", "BMP", "TIFF", "SVG", "PDF", "", None])
def test_rechaza_otros_formatos(formato):
    with pytest.raises(FotoInvalidaError, match="JPG, PNG o WebP"):
        _valida(formato=formato)


def test_rechaza_archivos_demasiado_pesados():
    with pytest.raises(FotoInvalidaError, match="5 MB"):
        _valida(tamano=MAX_BYTES_SUBIDA + 1)


def test_acepta_justo_el_tope_de_peso():
    _valida(tamano=MAX_BYTES_SUBIDA)


def test_rechaza_archivos_vacios():
    with pytest.raises(FotoInvalidaError, match="vacío"):
        _valida(tamano=0)


def test_rechaza_imagenes_con_demasiados_pixeles():
    # Protege al servidor de una «bomba de descompresión»: pesa poco pero ocupa mucha memoria
    with pytest.raises(FotoInvalidaError, match="demasiado grande"):
        _valida(ancho=10_000, alto=MAX_PIXELES // 10_000 + 1)


def test_rechaza_imagenes_muy_pequenas():
    with pytest.raises(FotoInvalidaError, match=str(MIN_LADO)):
        _valida(ancho=MIN_LADO - 1, alto=800)
    with pytest.raises(FotoInvalidaError, match=str(MIN_LADO)):
        _valida(ancho=800, alto=MIN_LADO - 1)


def test_acepta_justo_el_lado_minimo():
    _valida(ancho=MIN_LADO, alto=MIN_LADO)


@pytest.mark.parametrize(("ancho", "alto"), [(0, 100), (100, 0), (-5, 100)])
def test_rechaza_dimensiones_imposibles(ancho, alto):
    with pytest.raises(FotoInvalidaError):
        _valida(ancho=ancho, alto=alto)


def test_el_mensaje_de_error_habla_en_espanol_para_la_persona_que_sube():
    with pytest.raises(FotoInvalidaError) as error:
        _valida(formato="GIF")
    assert str(error.value).endswith(".")  # una oración completa, apta para mostrar en el panel


# ───────────── Recorte cuadrado ─────────────


@pytest.mark.parametrize(
    ("ancho", "alto", "caja"),
    [
        (800, 600, (100, 0, 700, 600)),  # horizontal: se pierde un poco a los lados
        (600, 800, (0, 100, 600, 700)),  # vertical: se pierde arriba y abajo
        (500, 500, (0, 0, 500, 500)),  # ya cuadrada: no se toca
        (1001, 1000, (0, 0, 1000, 1000)),  # diferencia impar: el sobrante cae a un lado
    ],
)
def test_recorta_al_cuadrado_desde_el_centro(ancho, alto, caja):
    assert recorte_cuadrado(ancho, alto) == caja


@pytest.mark.parametrize(("ancho", "alto"), [(1, 1), (300, 900), (4000, 3000), (999, 1000)])
def test_el_recorte_siempre_es_cuadrado_y_cabe_en_la_imagen(ancho, alto):
    izq, arriba, der, abajo = recorte_cuadrado(ancho, alto)
    assert der - izq == abajo - arriba == min(ancho, alto)
    assert 0 <= izq and 0 <= arriba and der <= ancho and abajo <= alto


def test_el_recorte_rechaza_dimensiones_imposibles():
    with pytest.raises(ValueError):
        recorte_cuadrado(0, 10)


def test_la_miniatura_es_un_lado_razonable_para_celular():
    assert 200 <= LADO_MINIATURA <= 640  # nítida en pantallas densas, liviana en 3G
