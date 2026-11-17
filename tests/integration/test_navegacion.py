"""Navegación del núcleo: enlaces visibles según la sesión y el rol."""

import re

import pytest
from django.urls import reverse

from apps.cuentas.models import Usuario

pytestmark = pytest.mark.integration


def test_navegacion_publica(client, db):
    html = client.get(reverse("comparacion:inicio")).content.decode()
    for ruta in ["comparacion:productos", "establecimientos:directorio", "cuentas:ingresar"]:
        assert f'href="{reverse(ruta)}"' in html
    assert reverse("moderacion:bandeja") not in html


def test_menu_de_cuenta_para_reportantes(client, reportante):
    client.force_login(reportante)
    html = client.get(reverse("comparacion:inicio")).content.decode()
    assert f'href="{reverse("precios:mis_aportes")}"' in html
    assert f'href="{reverse("cuentas:mis_datos")}"' in html
    assert reverse("moderacion:bandeja") not in html


def test_moderacion_en_el_menu_solo_para_moderadores(client, django_user_model):
    moderador = django_user_model.objects.create_user(
        username="mod", password="x-clave-1234", rol=Usuario.Rol.MODERADOR
    )
    client.force_login(moderador)
    html = client.get(reverse("comparacion:inicio")).content.decode()
    assert f'href="{reverse("moderacion:bandeja")}"' in html


def test_la_pagina_actual_se_marca(client, db):
    html = client.get(reverse("establecimientos:directorio")).content.decode()
    assert (
        f'href="{reverse("establecimientos:directorio")}"\n           aria-current="page"' in html
    )


def test_ningun_comentario_de_plantilla_se_muestra_en_la_pagina(client, reportante, arroz):
    # Django solo admite {# #} en una línea; uno de varias líneas se imprime como texto
    producto, _, _ = arroz
    client.force_login(reportante)
    for url in (
        reverse("comparacion:inicio"),
        reverse("comparacion:comparar", args=[producto.pk]),
        reverse("precios:registrar"),
    ):
        html = client.get(url).content.decode()
        assert "{#" not in html and "#}" not in html, url


def test_cabecera_tiene_menu_de_hamburguesa_accesible_y_deja_los_botones_a_la_vista(client, db):
    # En celular los enlaces van en un menú; «Ingresar» y «Crear cuenta» siguen visibles siempre.
    html = client.get(reverse("comparacion:inicio")).content.decode()
    assert 'id="nav-principal"' in html
    assert re.search(r'<button[^>]*class="menu-boton"[^>]*aria-controls="nav-principal"', html)
    assert 'aria-expanded="false"' in html
    assert re.search(r'<a class="btn btn-sec" href="[^"]*ingresar/">Ingresar</a>', html)
    assert re.search(r'<a class="btn" href="[^"]*registro/">Crear cuenta</a>', html)


def test_el_menu_de_hamburguesa_tambien_esta_con_sesion_iniciada(client, django_user_model):
    usuario = django_user_model.objects.create_user(
        username="menu1", password="clave-segura-123", acepto_tratamiento_datos=True
    )
    client.force_login(usuario)
    html = client.get(reverse("comparacion:inicio")).content.decode()
    assert 'aria-controls="nav-principal"' in html and "menu-cuenta" in html


def test_enter_en_el_buscador_de_la_portada_lleva_a_los_resultados(client, db):
    """Enter en la barra de búsqueda debe enviar la consulta a la lista de productos."""
    html = client.get(reverse("comparacion:inicio")).content.decode()
    formulario = re.search(r'<form[^>]*role="search"[^>]*>(.*?)</form>', html, flags=re.DOTALL)
    assert formulario, "el buscador no está dentro de un formulario de búsqueda"
    etiqueta = re.search(r"<form[^>]*role=\"search\"[^>]*>", html).group(0)
    assert 'method="get"' in etiqueta
    assert f'action="{reverse("comparacion:productos")}"' in etiqueta
    assert 'name="q"' in formulario.group(1)
