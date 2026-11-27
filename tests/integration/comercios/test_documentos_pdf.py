"""Evidencia del comercio en PDF (ADR-0034, RF-C02): subida, descarga solo para moderación,
borrado al decidir y nada de los documentos en respuestas públicas (M-13, M-15)."""

import hashlib
import re

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.urls import reverse

from apps.comercios import services
from apps.comercios.domain.documentos import MAX_BYTES_DOCUMENTO
from apps.comercios.models import DocumentoComercio, PerfilComercio
from tests.integration.comercios.pdf import CAMARA, RUT, archivo, pdfs

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

HTMX = {"HTTP_HX_REQUEST": "true"}
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


def _enviar(client, tienda, **documentos):
    datos = {"establecimiento": tienda.pk, "nombre_contacto": "Rosa", "telefono": "3001234567"}
    datos.update({k: v for k, v in pdfs(**documentos).items() if v is not None})
    return client.post(reverse("comercios:crear_perfil"), datos, **HTMX)


def _error_del_campo(html: str, campo: str) -> str:
    encontrado = re.search(rf'<span class="error" id="id_{campo}_error"[^>]*>([^<]+)</span>', html)
    return encontrado.group(1) if encontrado else ""


def _url(perfil, tipo="rut"):
    return reverse("comercios:documento_perfil", args=[perfil.pk, tipo])


@pytest.fixture
def pendiente(duena, tiendas):
    return services.crear_perfil(
        usuario=duena, establecimiento_id=tiendas[0].pk, nombre_contacto="Rosa", **pdfs()
    )


# ---------- Subida ----------


def test_el_formulario_pide_los_dos_pdf_con_etiqueta_y_multipart(client, duena, tiendas):
    client.force_login(duena)
    html = client.get(reverse("comercios:inicio")).content.decode()
    assert "Certificado de Cámara de Comercio (PDF)" in html and "RUT (PDF)" in html
    assert html.count('type="file"') == 2 and 'accept="application/pdf' in html
    assert 'enctype="multipart/form-data"' in html and 'hx-encoding="multipart/form-data"' in html
    assert "hx-disabled-elt" in html
    assert '<label for="id_camara_comercio">' in html and '<label for="id_rut">' in html
    assert "Evidencia de que representas" not in html
    assert "tus documentos solo para la verificación" in html


def test_subida_valida_crea_el_perfil_con_los_dos_documentos(client, duena, tiendas):  # M-13
    client.force_login(duena)
    respuesta = _enviar(client, tiendas[0])
    assert respuesta.status_code == 200 and "en revisión" in respuesta.content.decode()
    perfil = PerfilComercio.objects.get()
    documentos = {d.tipo: d for d in perfil.documentos.all()}
    assert set(documentos) == {"camara_comercio", "rut"}
    assert bytes(documentos["rut"].contenido) == RUT and documentos["rut"].tamano == len(RUT)
    assert documentos["camara_comercio"].sha256 == hashlib.sha256(CAMARA).hexdigest()
    assert all(d.borrado_en is None for d in documentos.values())


@pytest.mark.parametrize(
    ("campo", "documento", "mensaje"),
    [
        ("rut", archivo("rut.pdf", PNG, "image/png"), "no es un PDF válido"),
        ("rut", archivo("rut.png", PNG, "image/png"), "debe ser un PDF"),
        ("camara_comercio", archivo("c.pdf.exe", CAMARA), "debe ser un PDF"),
        (
            "camara_comercio",
            archivo("grande.pdf", b"%PDF-1.7\n" + b"0" * MAX_BYTES_DOCUMENTO),
            "más de 2 MB",
        ),
        ("rut", None, "Adjunta el RUT en PDF."),
        ("camara_comercio", None, "Adjunta el certificado de Cámara de Comercio en PDF."),
    ],
)
def test_un_archivo_invalido_o_faltante_no_crea_nada_y_marca_el_campo(
    client, duena, tiendas, campo, documento, mensaje
):
    client.force_login(duena)
    html = _enviar(client, tiendas[0], **{campo: documento}).content.decode()
    assert mensaje in _error_del_campo(html, campo)
    assert f'aria-describedby="id_{campo}_helptext id_{campo}_error"' in html
    assert not PerfilComercio.objects.exists() and not DocumentoComercio.objects.exists()


def test_el_servicio_tambien_valida_y_no_deja_nada_a_medias(duena, tiendas):
    with pytest.raises(ValidationError, match="RUT"):
        services.crear_perfil(
            usuario=duena,
            establecimiento_id=tiendas[0].pk,
            nombre_contacto="Rosa",
            **pdfs(rut=archivo("rut.pdf", PNG)),
        )
    assert not PerfilComercio.objects.exists() and not DocumentoComercio.objects.exists()


def test_la_bd_impide_un_documento_de_mas_de_2_mb_o_repetido(pendiente):
    with pytest.raises(IntegrityError), transaction.atomic():
        DocumentoComercio.objects.filter(perfil=pendiente, tipo="rut").update(
            tamano=MAX_BYTES_DOCUMENTO + 1
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        DocumentoComercio.objects.create(
            perfil=pendiente, tipo="rut", contenido=RUT, tamano=len(RUT), sha256="x"
        )


# ---------- Descarga: solo moderación ----------


def test_un_anonimo_no_descarga(client, pendiente):  # M-13
    respuesta = client.get(_url(pendiente))
    assert respuesta.status_code == 302 and "ingresar" in respuesta.url


def test_un_reportante_y_la_duena_reciben_404(client, pendiente, duena, reportante):  # M-15
    for usuario in (reportante, duena):
        client.force_login(usuario)
        respuesta = client.get(_url(pendiente))
        assert respuesta.status_code == 404 and RUT not in respuesta.content


def test_moderacion_ve_el_pdf_con_cabeceras_seguras(client, pendiente, moderador):
    client.force_login(moderador)
    respuesta = client.get(_url(pendiente, "camara_comercio"))
    assert respuesta.status_code == 200 and respuesta.content == CAMARA
    assert respuesta["Content-Type"] == "application/pdf"
    disposicion = f'inline; filename="camara-comercio-{pendiente.pk}.pdf"'
    assert respuesta["Content-Disposition"] == disposicion
    assert respuesta["X-Content-Type-Options"] == "nosniff"
    assert respuesta["Cache-Control"] == "private, no-store"
    assert client.get(_url(pendiente, "otro")).status_code == 404


def test_la_bandeja_enlaza_los_dos_documentos_con_su_tamano(client, pendiente, moderador):
    client.force_login(moderador)
    html = client.get(reverse("comercios:verificacion")).content.decode()
    assert "Ver Cámara de Comercio" in html and "Ver RUT" in html
    assert _url(pendiente) in html and _url(pendiente, "camara_comercio") in html
    assert "bytes" in html  # tamaño con filesizeformat
    assert "Evidencia: «" not in html


# ---------- Minimización al decidir ----------


@pytest.mark.parametrize("aprobar", [True, False])
def test_al_decidir_se_borran_los_bytes_y_queda_la_constancia(pendiente, moderador, aprobar):
    antes = {d.tipo: d.sha256 for d in pendiente.documentos.all()}
    services.verificar_perfil(
        moderador=moderador, perfil_id=pendiente.pk, aprobar=aprobar, motivo="No coincide"
    )
    documentos = list(DocumentoComercio.objects.filter(perfil=pendiente))
    assert len(documentos) == 2
    assert all(d.contenido is None and d.borrado_en is not None for d in documentos)
    assert {d.tipo: d.sha256 for d in documentos} == antes
    assert all(d.tamano > 0 for d in documentos)


def test_si_la_decision_falla_no_se_borra_nada(pendiente, moderador):
    with pytest.raises(ValidationError):
        services.verificar_perfil(moderador=moderador, perfil_id=pendiente.pk, aprobar=False)
    assert all(d.contenido is not None for d in pendiente.documentos.all())


def test_un_documento_borrado_muestra_un_mensaje_amable(client, pendiente, moderador):
    services.verificar_perfil(moderador=moderador, perfil_id=pendiente.pk, aprobar=True)
    client.force_login(moderador)
    respuesta = client.get(_url(pendiente))
    html = respuesta.content.decode()
    assert respuesta.status_code == 410 and "ya no está disponible" in html
    assert respuesta["Content-Type"].startswith("text/html")


# ---------- Nada en respuestas públicas (M-15) ----------


def test_ninguna_respuesta_publica_contiene_los_documentos(
    client, api, pendiente, moderador, arroz
):  # M-15
    services.verificar_perfil(moderador=moderador, perfil_id=pendiente.pk, aprobar=True)
    documentos = list(pendiente.documentos.all())
    privados = [d.sha256 for d in documentos] + ["Certificado Camara.pdf", "RUT-DIAN.PDF"]
    respuestas = [
        api.get(reverse("api-comparacion", args=[arroz[0].pk])),
        client.get(reverse("comparacion:comparar", args=[arroz[0].pk])),
        client.get(reverse("comparacion:establecimiento", args=[pendiente.establecimiento_id])),
    ]
    for respuesta in respuestas:
        assert respuesta.status_code == 200
        assert RUT not in respuesta.content and CAMARA not in respuesta.content
        texto = respuesta.content.decode()
        assert not [p for p in privados if p in texto]
