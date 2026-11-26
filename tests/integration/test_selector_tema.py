"""Selector de apariencia (automática, clara u oscura): accesible y sin romper el automático."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def _inicio(client) -> str:
    return client.get(reverse("comparacion:inicio")).content.decode()


def test_el_pie_ya_no_repite_el_selector_de_apariencia(client):
    html = _inicio(client)
    pie = html.split('<footer class="pie"')[1].split("</footer>")[0]
    assert "Apariencia" not in pie and "data-tema=" not in pie  # un solo control: el de la barra


def test_la_cabecera_tiene_boton_con_nombre_accesible(client):
    html = _inicio(client)
    assert 'class="tema-alternar"' in html
    assert 'aria-label="Cambiar a modo oscuro"' in html


def test_la_preferencia_se_aplica_antes_de_pintar_para_evitar_parpadeo(client):
    html = _inicio(client)
    assert html.index("ahorrapues-tema") < html.index("css/app.css")
    assert "js/tema.js" in html
