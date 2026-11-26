"""La portada invita a registrar un precio y la barra superior no lo repite ahí (PUX-01, M-01)."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def _barra(html: str) -> str:
    return html.split("</header>")[0]


def _hero(html: str) -> str:
    return html.split('class="hero-acciones"')[1].split("</div>")[0]


def test_el_boton_principal_de_la_portada_es_registrar_precio_sin_cuenta(client):
    hero = _hero(client.get(reverse("comparacion:inicio")).content.decode())
    assert 'href="/precios/registrar/"' in hero and ">Registrar precio<" in hero
    assert "Crear cuenta gratis" not in hero


def test_y_tambien_con_cuenta(client, reportante):
    client.force_login(reportante)
    hero = _hero(client.get(reverse("comparacion:inicio")).content.decode())
    assert 'href="/precios/registrar/"' in hero and ">Registrar precio<" in hero


def test_en_la_portada_la_barra_no_repite_registrar_precio(client):
    barra = _barra(client.get(reverse("comparacion:inicio")).content.decode())
    assert "btn-registrar" not in barra
    assert "Ingresar" in barra and "Crear cuenta" in barra  # el acceso a la cuenta sigue ahí


@pytest.mark.parametrize("ruta", ["comparacion:productos", "establecimientos:directorio"])
def test_en_las_demas_paginas_la_barra_conserva_registrar_precio(client, ruta):
    barra = _barra(client.get(reverse(ruta)).content.decode())
    assert "btn-registrar" in barra  # la acción principal sigue a la vista (PUX-01)


def test_quien_toca_registrar_precio_sin_cuenta_pasa_por_ingresar_y_vuelve(client):
    r = client.get(reverse("precios:registrar"))
    assert r.status_code == 302
    assert r.url == "/cuentas/ingresar/?next=/precios/registrar/"
