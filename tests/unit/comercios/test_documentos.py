"""Evidencia de los comercios en PDF (ADR-0034, RF-C02). Python puro — TDD.

Solo se acepta un PDF de verdad: extensión .pdf (sin importar mayúsculas), cabecera «%PDF-» y
entre 1 byte y 2 MB (Vercel corta en 4,5 MB por petición y van dos archivos).
"""

import pytest

from apps.comercios.domain.documentos import (
    MAX_BYTES_DOCUMENTO,
    DocumentoInvalidoError,
    validar_pdf,
)

pytestmark = pytest.mark.unit
PDF = b"%PDF-1.7\n"
PNG = b"\x89PNG\r\n\x1a\n"


def test_el_limite_es_de_2_mb():
    assert MAX_BYTES_DOCUMENTO == 2 * 1024 * 1024


@pytest.mark.parametrize("nombre", ["rut.pdf", "RUT.PDF", "camara.Pdf", "certificado 2026.pdf"])
def test_acepta_un_pdf_sin_importar_mayusculas(nombre):
    assert validar_pdf(nombre, 1234, PDF) is None


def test_acepta_exactamente_2_mb():
    validar_pdf("rut.pdf", MAX_BYTES_DOCUMENTO, PDF)


def test_acepta_1_byte():
    validar_pdf("rut.pdf", 1, PDF)


def test_rechaza_2_mb_mas_un_byte():
    with pytest.raises(DocumentoInvalidoError, match="2 MB"):
        validar_pdf("rut.pdf", MAX_BYTES_DOCUMENTO + 1, PDF)


@pytest.mark.parametrize("tamano", [0, -1])
def test_rechaza_un_archivo_vacio_o_tamano_negativo(tamano):
    with pytest.raises(DocumentoInvalidoError, match="vacío"):
        validar_pdf("rut.pdf", tamano, PDF)


@pytest.mark.parametrize("nombre", ["rut.pdf.exe", "rut.png", "rut", "rut.pdfx", ".pdf"])
def test_rechaza_otra_extension(nombre):
    with pytest.raises(DocumentoInvalidoError, match="PDF"):
        validar_pdf(nombre, 1234, PDF)


@pytest.mark.parametrize("nombre", ["", "   "])
def test_rechaza_un_nombre_vacio(nombre):
    with pytest.raises(DocumentoInvalidoError):
        validar_pdf(nombre, 1234, PDF)


def test_rechaza_un_png_renombrado_a_pdf():
    with pytest.raises(DocumentoInvalidoError, match="no es un PDF"):
        validar_pdf("rut.pdf", 1234, PNG)


@pytest.mark.parametrize("cabecera", [b"", b"%PDF", b" %PDF-1.4", b"%pdf-1.4"])
def test_rechaza_una_cabecera_incompleta_o_distinta(cabecera):
    with pytest.raises(DocumentoInvalidoError):
        validar_pdf("rut.pdf", 1234, cabecera)


def test_el_error_es_un_value_error_con_mensaje_para_mostrar():
    with pytest.raises(ValueError) as error:
        validar_pdf("rut.png", 10, PDF)
    assert str(error.value).endswith(".")
