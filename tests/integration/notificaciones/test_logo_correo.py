"""Logo de los correos: imagen con URL absoluta y alt legible si el cliente bloquea imágenes."""

import re

import pytest
from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static
from django.urls import reverse

from apps.notificaciones.domain.catalogo import Tipo
from apps.notificaciones.services import renderizar
from apps.notificaciones.views import EJEMPLOS

pytestmark = pytest.mark.integration
IMG = re.compile(r"<img\b[^>]*>", re.S)
SRC = re.compile(r'src="([^"]+)"')
LOGO = "img/logo-horizontal-600.png"


def _logo(html: str) -> str:
    etiquetas = IMG.findall(html)
    assert len(etiquetas) == 1, etiquetas
    return etiquetas[0]


@pytest.mark.parametrize("tipo", list(Tipo))
def test_cada_correo_lleva_el_logo_con_url_absoluta(db, tipo):
    _, _, html = renderizar(tipo, dict(EJEMPLOS[tipo]))
    etiqueta = _logo(html)
    src = SRC.search(etiqueta).group(1)
    # Sin depender del hash: en pruebas el storage no es el de manifiesto
    assert src.startswith(settings.SITIO_URL + "/") and src.endswith(".png"), src
    assert src == settings.SITIO_URL + static(LOGO)
    assert 'alt="AhorraPues"' in etiqueta
    # Si el cliente bloquea imágenes, el alt se ve como el nombre en negrita
    assert "font-weight:700" in etiqueta and "color:#1d1d1f" in etiqueta
    assert 'width="180"' in etiqueta and "border:0" in etiqueta
    # El logo enlaza al sitio
    assert f'<a href="{settings.SITIO_URL}/" style="text-decoration:none;">' in html


@pytest.mark.parametrize("tipo", list(Tipo))
def test_ya_no_esta_el_cuadro_con_la_letra_a(db, tipo):
    _, _, html = renderizar(tipo, dict(EJEMPLOS[tipo]))
    assert ">A</td>" not in html
    assert "background-color:#1d1d1f;border-radius:10px" not in html
    # El encabezado conserva su celda: fondo, borde azul y esquinas redondeadas
    assert 'bgcolor="#eaf3fd"' in html and "border-top:4px solid #0071e3" in html
    assert "border-radius:28px 28px 0 0" in html and "padding:20px 32px" in html


@pytest.mark.parametrize("tipo", list(Tipo))
def test_la_version_de_texto_no_cambia(db, tipo):
    _, texto, _ = renderizar(tipo, dict(EJEMPLOS[tipo]))
    assert texto.startswith("AhorraPues\n==========\n")
    assert "logo-horizontal" not in texto and ".png" not in texto and "/static/" not in texto


def test_el_logo_existe_en_los_estaticos():
    assert finders.find(LOGO), "falta static/img/logo-horizontal-600.png"


def test_la_vista_previa_muestra_el_logo(client, django_user_model):
    staff = django_user_model.objects.create_user(
        username="staff-logo", password="x-clave-1234", is_staff=True
    )
    client.force_login(staff)
    respuesta = client.get(reverse("correos:vista_previa", args=["bienvenida"]))
    assert respuesta.status_code == 200
    html = respuesta.content.decode()
    assert "Te damos la bienvenida" in html
    assert SRC.search(_logo(html)).group(1) == settings.SITIO_URL + static(LOGO)
