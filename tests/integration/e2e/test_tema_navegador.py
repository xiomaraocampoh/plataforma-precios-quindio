"""Un solo control de apariencia, siempre en la barra (también en celular), y sin desbordes."""

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)

ANCHOS = [340, 360, 390, 440, 480, 520, 540, 600, 680, 720, 800, 900, 1023, 1024, 1100, 1280]


def _sin_desborde(page):
    page.wait_for_load_state("networkidle")  # con la hoja de estilos ya asentada
    return not page.evaluate("document.documentElement.scrollWidth > innerWidth")


@pytest.mark.parametrize("ancho", [360, 390, 440, 521, 768, 1280])
def test_el_boton_esta_en_la_barra_en_todos_los_anchos(page, live_server, ancho):
    page.set_viewport_size({"width": ancho, "height": 800})
    page.goto(live_server.url + "/productos/")
    expect(page.locator(".tema-alternar")).to_be_visible()
    assert page.locator(".tema-alternar").bounding_box()["width"] >= 36  # tocable
    assert page.locator(".tema-menu").count() == 0  # ya no hay un segundo control dentro del menú


@pytest.mark.parametrize("ancho", [390, 1280])
def test_cambia_el_tema_y_la_eleccion_se_recuerda(page, live_server, ancho):
    page.set_viewport_size({"width": ancho, "height": 800})
    page.emulate_media(color_scheme="light")
    page.goto(live_server.url + "/")
    page.click(".tema-alternar")
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"
    page.reload()
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"
    page.click(".tema-alternar")
    assert page.evaluate("document.documentElement.dataset.theme") == "light"


def test_la_barra_no_desborda_en_ningun_ancho_ni_con_sesion(page, pagina_con_sesion, live_server):
    for pagina in (page, pagina_con_sesion):
        for ancho in ANCHOS:
            pagina.set_viewport_size({"width": ancho, "height": 700})
            pagina.goto(live_server.url + "/productos/")
            assert _sin_desborde(pagina), f"la barra desborda a {ancho} px"
