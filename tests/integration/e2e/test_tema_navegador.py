"""El botón de sol/luna de la barra es el único control de apariencia, también en celular."""

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize("ancho", [360, 390, 768, 1280])
def test_el_boton_se_ve_en_todos_los_anchos_y_sin_desbordar(page, live_server, ancho):
    page.set_viewport_size({"width": ancho, "height": 800})
    page.goto(live_server.url + "/productos/")
    expect(page.locator(".tema-alternar")).to_be_visible()
    assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")


def test_el_boton_cabe_con_la_sesion_iniciada_en_un_celular_angosto(pagina_con_sesion, live_server):
    page = pagina_con_sesion
    page.set_viewport_size({"width": 360, "height": 800})
    page.goto(live_server.url + "/productos/")
    expect(page.locator(".tema-alternar")).to_be_visible()
    assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")


def test_cambia_el_tema_y_la_eleccion_se_recuerda(page, live_server):
    page.set_viewport_size({"width": 390, "height": 800})
    page.emulate_media(color_scheme="light")
    page.goto(live_server.url + "/")
    page.click(".tema-alternar")
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"
    page.reload()
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"
    page.click(".tema-alternar")
    assert page.evaluate("document.documentElement.dataset.theme") == "light"
