"""La cuenta vive dentro del menú ☰ donde hay hamburguesa (hasta 1023 px) y en un desplegable fuera."""

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)

ENLACES = ["Mis aportes", "Mis datos", "Seguridad"]


def _ir(pagina, live_server, ancho, ruta="/productos/"):
    pagina.set_viewport_size({"width": ancho, "height": 800})
    pagina.goto(live_server.url + ruta)
    pagina.wait_for_load_state("networkidle")


@pytest.mark.parametrize("ancho", [360, 390, 768, 1023])
def test_con_hamburguesa_la_cuenta_no_esta_suelta_en_la_barra(
    pagina_con_sesion, live_server, ancho
):
    pagina = pagina_con_sesion
    _ir(pagina, live_server, ancho)
    expect(pagina.locator(".menu-cuenta")).to_be_hidden()  # nada de «Mlondono408 ▾» en la barra
    pagina.click(".menu-boton")
    grupo = pagina.locator(".nav-cuenta")
    expect(grupo).to_be_visible()
    expect(grupo).to_contain_text("reportante1")  # se ve a nombre de quién se entra
    for texto in ENLACES + ["Salir"]:
        expect(grupo.get_by_text(texto, exact=True)).to_be_visible()
    assert not pagina.evaluate("document.documentElement.scrollWidth > innerWidth")


@pytest.mark.parametrize("ancho", [1024, 1280])
def test_en_escritorio_sigue_el_desplegable_y_no_se_duplica(pagina_con_sesion, live_server, ancho):
    pagina = pagina_con_sesion
    _ir(pagina, live_server, ancho)
    expect(pagina.locator(".menu-cuenta")).to_be_visible()
    expect(pagina.locator(".nav-cuenta")).to_be_hidden()
    pagina.click(".menu-cuenta summary")
    expect(pagina.locator(".menu-cuenta").get_by_text("Mis aportes")).to_be_visible()


def test_el_enlace_del_menu_lleva_a_su_pagina(pagina_con_sesion, live_server):
    pagina = pagina_con_sesion
    _ir(pagina, live_server, 390)
    pagina.click(".menu-boton")
    pagina.locator(".nav-cuenta").get_by_text("Mis aportes", exact=True).click()
    pagina.wait_for_url("**/precios/mis-aportes/")


def test_salir_desde_el_menu_cierra_la_sesion(pagina_con_sesion, live_server):
    pagina = pagina_con_sesion
    _ir(pagina, live_server, 390)
    pagina.click(".menu-boton")
    pagina.locator(".nav-cuenta").get_by_role("button", name="Salir").click()
    pagina.wait_for_load_state("networkidle")
    expect(pagina.get_by_role("link", name="Ingresar").first).to_be_visible()
    assert pagina.locator(".nav-cuenta").count() == 0  # ya no hay cuenta


def test_sin_sesion_no_hay_grupo_de_cuenta(page, live_server):
    _ir(page, live_server, 390)
    assert page.locator(".nav-cuenta").count() == 0 and page.locator(".menu-cuenta").count() == 0
