"""La barra superior en un navegador real: logo grande, enlace activo visible, sombra al bajar."""

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)


def _ir(page, live_server, ruta="/", ancho=1280):
    page.set_viewport_size({"width": ancho, "height": 800})
    page.goto(live_server.url + ruta)
    page.add_style_tag(content=".asistente-widget{display:none !important}")


def test_el_logo_es_grande_en_escritorio(page, live_server):
    _ir(page, live_server)
    caja = page.locator(".marca-logo-ancho:visible").first.bounding_box()
    assert caja["height"] >= 46 and caja["width"] >= 170


def test_la_barra_es_mas_alta_para_el_logo(page, live_server):
    _ir(page, live_server)
    assert page.locator("header.cabecera").bounding_box()["height"] >= 64


def test_el_enlace_de_la_pagina_actual_tiene_una_pastilla_visible(page, live_server):
    _ir(page, live_server, "/productos/")
    activo = page.locator(".nav a[aria-current=page]")
    expect(activo).to_have_count(1)
    fondo = activo.evaluate("e => getComputedStyle(e).backgroundColor")
    assert fondo not in ("rgba(0, 0, 0, 0)", "transparent")  # no depende solo del color del texto
    assert activo.evaluate("e => getComputedStyle(e).fontWeight") in ("600", "700")


def test_la_sombra_aparece_al_bajar_y_se_va_arriba(page, live_server):
    _ir(page, live_server)
    barra = page.locator("header.cabecera")
    expect(barra).not_to_have_class("cabecera sombra")
    assert "sombra" not in barra.get_attribute("class")
    page.evaluate("window.scrollTo(0, 600)")
    page.wait_for_function("document.querySelector('header.cabecera').classList.contains('sombra')")
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_function(
        "!document.querySelector('header.cabecera').classList.contains('sombra')"
    )


@pytest.mark.parametrize("ancho", [1024, 1100, 1280, 1440])
@pytest.mark.parametrize("ruta", ["/", "/productos/"])
def test_en_escritorio_todo_cabe_en_una_sola_fila_sin_desbordar(page, live_server, ruta, ancho):
    _ir(page, live_server, ruta, ancho)
    assert page.locator(".cabecera-in").bounding_box()["height"] <= 96  # una fila
    assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")


@pytest.mark.parametrize("ancho", [390, 768])
def test_en_celular_y_tablet_sigue_la_hamburguesa_sin_desbordar(page, live_server, ancho):
    _ir(page, live_server, "/productos/", ancho)
    expect(page.locator(".menu-boton")).to_be_visible()
    assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
    assert page.locator(".cabecera-in").bounding_box()["height"] <= 80


@pytest.mark.parametrize("ancho", [1280, 1440, 1600])
def test_la_pastilla_esta_centrada_y_el_logo_pegado_a_la_izquierda(page, live_server, ancho):
    _ir(page, live_server, "/productos/", ancho)
    nav = page.locator(".nav").bounding_box()
    centro = nav["x"] + nav["width"] / 2
    assert abs(centro - ancho / 2) <= 3  # centrada en la pantalla
    logo = page.locator(".marca").bounding_box()
    assert logo["x"] <= 80  # a la izquierda, pero sin quedar pegado al borde
    if ancho >= 1440:
        assert logo["x"] >= 36  # respira: no queda tan a la izquierda
    assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
