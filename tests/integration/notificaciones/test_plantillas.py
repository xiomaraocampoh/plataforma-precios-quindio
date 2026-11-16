"""Plantillas de correo: HTML accesible y compatible, texto plano sin etiquetas, vista previa."""

import re

import pytest
from django.urls import reverse

from apps.notificaciones.domain.catalogo import Categoria, Tipo, categoria_de
from apps.notificaciones.services import renderizar
from apps.notificaciones.views import EJEMPLOS

pytestmark = pytest.mark.integration
ETIQUETA = re.compile(r"</?[a-zA-Z][^>]*>")


@pytest.mark.parametrize("tipo", list(Tipo))
def test_cada_correo_tiene_html_y_texto(db, tipo):
    asunto, texto, html = renderizar(tipo, dict(EJEMPLOS[tipo]))
    assert asunto and "\n" not in asunto and "{" not in asunto
    # HTML: compatible con clientes de correo y accesible
    assert '<html lang="es-CO"' in html
    assert 'role="presentation"' in html
    assert "max-width:560px" in html and "border-radius:28px" in html
    assert "background-color:#f5f5f7" in html and "#0071e3" in html
    assert "AhorraPues · Armenia, Quindío" in html
    assert "display:none" in html  # preheader oculto con el resumen
    assert "<img" not in html  # nada de información solo en imágenes
    assert "{{" not in html and "{%" not in html
    # Texto: siempre presente y sin etiquetas
    assert texto.strip()
    assert ETIQUETA.search(texto) is None, ETIQUETA.search(texto)
    assert "&amp;" not in texto and "&#x27;" not in texto
    assert "AhorraPues · Armenia, Quindío" in texto


@pytest.mark.parametrize("tipo", list(Tipo))
def test_el_pie_de_preferencias_solo_va_en_los_informativos(db, tipo):
    _, texto, html = renderizar(tipo, dict(EJEMPLOS[tipo]))
    informativo = categoria_de(tipo) == Categoria.INFORMATIVO
    assert ("Elegir qué correos recibo" in html) is informativo
    assert ("Elegir qué correos recibo" in texto) is informativo


def test_el_boton_trae_el_enlace_en_texto_por_si_no_carga(db):
    _, texto, html = renderizar(Tipo.VERIFICAR_CORREO, dict(EJEMPLOS[Tipo.VERIFICAR_CORREO]))
    enlace = EJEMPLOS[Tipo.VERIFICAR_CORREO]["enlace"]
    assert html.count(f'href="{enlace}"') == 2  # botón + enlace en texto
    assert "border-radius:999px" in html and "padding:14px 28px" in html
    assert f"Confirmar mi correo: {enlace}" in texto


def test_los_chips_dicen_el_estado_con_texto_y_color(db):
    datos = dict(EJEMPLOS[Tipo.REPORTE_MODERADO])
    _, _, aprobado = renderizar(Tipo.REPORTE_MODERADO, {**datos, "aprobado": True})
    _, _, rechazado = renderizar(Tipo.REPORTE_MODERADO, {**datos, "aprobado": False})
    assert "Publicado" in aprobado and "#e6f5ea" in aprobado and "#1c7a3d" in aprobado
    assert "No publicado" in rechazado and "#fdeceb" in rechazado and "#b3261e" in rechazado


def test_el_codigo_se_ve_grande_y_nunca_va_en_el_asunto(db):
    asunto, texto, html = renderizar(
        Tipo.CODIGO_VERIFICACION, {"codigo": "482913", "proposito": "ingresar"}
    )
    assert "482913" not in asunto
    assert "482913" in html and "482913" in texto
    assert "font-size:32px" in html


def test_vista_previa_solo_para_staff(client, django_user_model, reportante):
    url = reverse("correos:vista_previa", args=["bienvenida"])
    assert client.get(url).status_code == 403
    client.force_login(reportante)
    assert client.get(url).status_code == 403
    staff = django_user_model.objects.create_user(
        username="staff1", password="x-clave-1234", is_staff=True
    )
    client.force_login(staff)
    assert client.get(reverse("correos:indice")).status_code == 200
    html = client.get(url).content.decode()
    assert "Te damos la bienvenida" in html
    texto = client.get(url, {"formato": "texto"})
    assert texto["Content-Type"].startswith("text/plain")
    assert client.get(reverse("correos:vista_previa", args=["no-existe"])).status_code == 404
