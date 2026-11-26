"""Selector de apariencia (automática, clara u oscura): accesible y sin romper el automático."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def _inicio(client) -> str:
    return client.get(reverse("comparacion:inicio")).content.decode()


def test_el_pie_ofrece_las_tres_apariencias_como_grupo_con_nombre(client):
    html = _inicio(client)
    assert 'role="group" aria-label="Apariencia"' in html
    for valor in ("auto", "light", "dark"):
        assert f'data-tema="{valor}"' in html
    assert html.count("aria-pressed=") >= 3  # estado visible para lectores de pantalla


def test_la_cabecera_tiene_boton_con_nombre_accesible(client):
    html = _inicio(client)
    assert 'class="tema-alternar"' in html
    assert 'aria-label="Cambiar a modo oscuro"' in html


def test_la_preferencia_se_aplica_antes_de_pintar_para_evitar_parpadeo(client):
    html = _inicio(client)
    assert html.index("ahorrapues-tema") < html.index("css/app.css")
    assert "js/tema.js" in html
