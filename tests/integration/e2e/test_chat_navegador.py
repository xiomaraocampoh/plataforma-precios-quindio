"""Usabilidad del chat de K-nasta en un navegador real: el mensaje se ve al instante.

La respuesta del servidor se retiene a propósito para mirar el momento justo después de enviar.
"""

import pytest
from playwright.sync_api import expect

from apps.precios import services

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def mercado(reportante, arroz, tiendas):
    _, _, p1kg = arroz
    services.registrar_reporte(
        autor=reportante, presentacion_id=p1kg.pk, establecimiento_id=tiendas[1].pk, precio=7000
    )


@pytest.fixture
def chat(page, live_server, mercado):
    """El chat abierto y un contenedor para retener la respuesta del servidor."""
    retenidas = []
    page.route("**/asistente/enviar/", lambda ruta: retenidas.append(ruta))
    page.set_default_timeout(10_000)
    page.goto(live_server.url + "/")
    page.click("[data-lanzador]")
    # htmx termina de preparar el formulario recién cargado: sin esperar, el envío sería nativo
    page.wait_for_function(
        """() => { const c = document.querySelector('[data-cuerpo]');
          return c && c.querySelector('#chat-mensaje') && !c.classList.contains('htmx-settling')
            && !c.classList.contains('htmx-swapping'); }"""
    )
    return page, retenidas


def _esperar_envio(page, retenidas):
    for _ in range(100):
        if retenidas:
            return retenidas[0]
        page.wait_for_timeout(50)
    raise AssertionError("El mensaje no llegó a enviarse.")


def test_al_enviar_el_mensaje_aparece_la_caja_se_vacia_y_se_ve_que_escribe(chat):
    page, retenidas = chat
    page.fill("#chat-mensaje", "2 kg arroz")
    page.keyboard.press("Enter")
    ruta = _esperar_envio(page, retenidas)

    # Con el servidor todavía sin responder:
    expect(page.locator("#chat-mensaje")).to_have_value("")
    expect(page.locator("#chat-hilo .burbuja.usuario")).to_have_text("2 kg arroz")
    expect(page.locator("#chat-hilo .puntos")).to_be_visible()  # «escribiendo…» dentro del hilo
    assert page.evaluate("document.activeElement.id") == "chat-mensaje"  # puede seguir escribiendo

    ruta.continue_()
    expect(page.locator("#chat-hilo .cc-res")).to_be_visible()
    # Sin duplicados: el mensaje provisional se reemplaza por el real
    expect(page.locator("#chat-hilo .burbuja.usuario")).to_have_count(1)
    expect(page.locator("#chat-hilo .puntos")).to_have_count(0)
    expect(page.locator("#chat-hilo .burbuja.asistente")).to_have_count(1)


def test_no_se_puede_enviar_otro_mensaje_mientras_se_espera_la_respuesta(chat):
    page, retenidas = chat
    page.fill("#chat-mensaje", "2 kg arroz")
    page.keyboard.press("Enter")
    _esperar_envio(page, retenidas)
    page.fill("#chat-mensaje", "y también leche")
    page.keyboard.press("Enter")
    page.wait_for_timeout(300)
    assert len(retenidas) == 1  # el segundo Enter no envía; el texto queda para después
    expect(page.locator("#chat-mensaje")).to_have_value("y también leche")


def test_si_falla_el_envio_el_texto_vuelve_a_la_caja_y_se_avisa(chat):
    page, retenidas = chat
    page.fill("#chat-mensaje", "2 kg arroz")
    page.keyboard.press("Enter")
    _esperar_envio(page, retenidas).abort()
    expect(page.locator("#chat-mensaje")).to_have_value("2 kg arroz")
    expect(page.locator("#chat-hilo .burbuja.usuario")).to_have_count(0)
    expect(page.locator("#chat-hilo .puntos")).to_have_count(0)
    expect(page.locator("#chat-hilo [data-error-envio]")).to_contain_text("No pude enviar")


def test_los_botones_de_respuesta_tambien_muestran_el_mensaje_al_instante(chat):
    page, retenidas = chat
    page.click(".atajo >> nth=0")  # «Registrar un precio»
    _esperar_envio(page, retenidas)
    expect(page.locator("#chat-hilo .burbuja.usuario")).to_contain_text("¿Cómo registro un precio?")
    expect(page.locator("#chat-hilo .puntos")).to_be_visible()


def test_enviar_mi_mercado_lleva_el_cursor_a_la_caja(chat):
    page, _ = chat
    page.click("[data-enviar-mercado]")
    assert page.evaluate("document.activeElement.id") == "chat-mensaje"
    assert page.url.endswith("/")  # no cambia de página ni agrega #chat-mensaje a la dirección
