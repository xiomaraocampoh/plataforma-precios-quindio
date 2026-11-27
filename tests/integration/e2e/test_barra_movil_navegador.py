"""En celular la barra usa el mismo logo horizontal que el computador (claro y oscuro)."""

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)


def _ir(page, live_server, ancho, esquema="light", ruta="/productos/"):
    page.set_viewport_size({"width": ancho, "height": 800})
    page.emulate_media(color_scheme=esquema)
    page.goto(live_server.url + ruta)
    page.wait_for_load_state("networkidle")


@pytest.mark.parametrize("ancho", [360, 390, 520, 600, 768])
def test_el_logo_horizontal_se_ve_en_celular_y_tablet(page, live_server, ancho):
    _ir(page, live_server, ancho)
    logo = page.locator(".marca-logo:visible")
    expect(logo).to_have_count(1)
    caja = logo.bounding_box()
    assert caja["width"] > caja["height"] * 3  # horizontal (con el nombre), no el ícono cuadrado
    assert caja["width"] >= 105  # legible
    assert page.locator(".marca-logo-icono").count() == 0


def test_en_oscuro_el_celular_usa_la_version_oscura_del_logo(page, live_server):
    _ir(page, live_server, 390, "dark")
    assert (
        page.locator(".logo-oscuro").is_visible() and not page.locator(".logo-claro").is_visible()
    )
    assert "oscuro" in page.locator(".logo-oscuro").get_attribute("src")


def test_en_claro_el_celular_usa_la_version_clara(page, live_server):
    _ir(page, live_server, 390, "light")
    assert (
        page.locator(".logo-claro").is_visible() and not page.locator(".logo-oscuro").is_visible()
    )


def test_el_nombre_del_logo_sigue_para_lectores_de_pantalla(page, live_server):
    _ir(page, live_server, 390)
    assert page.locator(".marca-nombre").inner_text() == "AhorraPues"  # oculto a la vista


@pytest.mark.parametrize("ancho", [360, 390])
def test_registrar_precio_sigue_a_la_vista_con_nombre_accesible(page, live_server, ancho):
    _ir(page, live_server, ancho)
    boton = page.get_by_role("link", name="Registrar")
    expect(boton.first).to_be_visible()
    assert boton.first.bounding_box()["height"] >= 40  # objetivo táctil
    assert page.locator(".menu-boton").is_visible()  # la hamburguesa sigue
