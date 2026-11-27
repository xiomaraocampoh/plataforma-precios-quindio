"""Un solo control de apariencia: en la barra (≥ 521 px) o en el menú ☰ (celulares angostos)."""

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)


def _sin_desborde(page):
    page.wait_for_load_state("networkidle")  # con la hoja de estilos ya asentada
    return not page.evaluate("document.documentElement.scrollWidth > innerWidth")


@pytest.mark.parametrize("ancho", [521, 768, 1280])
def test_en_pantallas_normales_el_boton_esta_en_la_barra(page, live_server, ancho):
    page.set_viewport_size({"width": ancho, "height": 800})
    page.goto(live_server.url + "/productos/")
    expect(page.locator(".tema-alternar")).to_be_visible()
    expect(page.locator(".tema-menu")).to_be_hidden()
    assert _sin_desborde(page)


@pytest.mark.parametrize("ancho", [360, 390, 440, 520])
@pytest.mark.parametrize("con_sesion", [False, True])
def test_en_celulares_angostos_va_dentro_del_menu_y_nada_desborda(
    page, pagina_con_sesion, live_server, ancho, con_sesion
):
    pagina = pagina_con_sesion if con_sesion else page
    pagina.set_viewport_size({"width": ancho, "height": 800})
    pagina.goto(live_server.url + "/productos/")
    expect(pagina.locator(".tema-alternar")).to_be_hidden()
    assert _sin_desborde(pagina)  # la barra cabe, también con el menú de usuario
    pagina.click(".menu-boton")
    expect(pagina.locator(".tema-menu")).to_be_visible()
    assert pagina.locator(".tema-menu").bounding_box()["height"] >= 44  # objetivo táctil


def test_cambia_el_tema_desde_el_menu_y_se_recuerda(page, live_server):
    page.set_viewport_size({"width": 390, "height": 800})
    page.emulate_media(color_scheme="light")
    page.goto(live_server.url + "/")
    page.click(".menu-boton")
    expect(page.locator(".tema-menu")).to_contain_text("Modo oscuro")
    page.click(".tema-menu")
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"
    expect(page.locator(".tema-menu")).to_contain_text("Modo claro")  # el texto dice qué hará
    page.reload()
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"


def test_cambia_el_tema_desde_la_barra_y_se_recuerda(page, live_server):
    page.set_viewport_size({"width": 1280, "height": 800})
    page.emulate_media(color_scheme="light")
    page.goto(live_server.url + "/")
    page.click(".tema-alternar")
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"
    page.reload()
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"
    page.click(".tema-alternar")
    assert page.evaluate("document.documentElement.dataset.theme") == "light"


ANCHOS = [340, 360, 390, 440, 480, 520, 540, 600, 680, 720, 800, 900, 1023, 1024, 1100, 1280]


def test_la_barra_no_desborda_en_ningun_ancho_ni_con_sesion(page, pagina_con_sesion, live_server):
    for pagina in (page, pagina_con_sesion):
        for ancho in ANCHOS:
            pagina.set_viewport_size({"width": ancho, "height": 700})
            pagina.goto(live_server.url + "/productos/")
            assert _sin_desborde(pagina), f"la barra desborda a {ancho} px"
