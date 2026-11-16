"""Accesibilidad WCAG 2.2 AA verificable en el HTML del servidor (M-03)."""

import re

import pytest
from django.urls import reverse

pytestmark = pytest.mark.integration

CAMPOS_VACIOS_PRECIO = {"establecimiento": "", "presentacion": "", "precio": "", "id_cliente": ""}


def _referencias_rotas(html: str) -> list[str]:
    """IDs citados por aria-describedby/labelledby/controls que no existen en la página."""
    ids = set(re.findall(r'\bid="([^"]+)"', html))
    citados = re.findall(r'aria-(?:describedby|labelledby|controls)="([^"]+)"', html)
    return sorted({ref for grupo in citados for ref in grupo.split()} - ids)


def test_registro_de_cuenta_asocia_ayudas_y_errores_a_sus_campos(client):
    # M-03 · 1.3.1: cada aria-describedby que genera Django debe apuntar a un elemento real
    vacio = client.get(reverse("cuentas:registro")).content.decode()
    con_errores = client.post(
        reverse("cuentas:registro"), {"username": "", "password1": "", "password2": ""}
    ).content.decode()
    assert _referencias_rotas(vacio) == []
    assert _referencias_rotas(con_errores) == []
    assert 'id="id_username_error"' in con_errores
    assert 'id="id_username_helptext"' in con_errores  # la ayuda sigue visible junto al error


def test_registro_de_precio_por_htmx_asocia_errores_a_sus_campos(client, reportante):
    # M-03 · 1.3.1 y 3.3.1, en el fragmento que devuelve HTMX
    client.force_login(reportante)
    html = client.post(
        reverse("precios:registrar"), CAMPOS_VACIOS_PRECIO, HTTP_HX_REQUEST="true"
    ).content.decode()
    assert html.count('aria-invalid="true"') == 3
    assert _referencias_rotas(html) == []


def test_ingreso_con_campos_vacios_muestra_un_error_por_campo(client):
    # M-03 · 3.3.1: antes la página se recargaba sin ningún mensaje
    html = client.post(
        reverse("cuentas:ingresar"), {"username": "", "password": ""}
    ).content.decode()
    assert html.count('aria-invalid="true"') == 2
    assert 'id="id_username_error"' in html
    assert 'id="id_password_error"' in html
    assert _referencias_rotas(html) == []


def test_inicio_ofrece_control_para_pausar_la_rotacion_del_titular(client, db):
    # M-03 · 2.2.2: el contenido en movimiento de más de 5 s debe poder detenerse
    html = client.get(reverse("comparacion:inicio")).content.decode()
    assert re.search(r'<button type="button"[^>]*id="pausar-rotacion"', html)
