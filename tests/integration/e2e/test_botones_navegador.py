"""Las acciones se ven como botones (no como enlaces con flecha) en las pantallas principales."""

import pytest

from apps.precios import services

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def datos(reportante, arroz, tiendas):
    prod, p500, _ = arroz
    services.registrar_reporte(
        autor=reportante, presentacion_id=p500.pk, establecimiento_id=tiendas[0].pk, precio=4500
    )
    return prod, tiendas[0]


def _como_boton(pagina, selector):
    """Cada elemento tiene forma de botón y no se subraya ni al pasar el mouse."""
    elementos = pagina.locator(selector)
    assert elementos.count() > 0, f"no hay «{selector}» en {pagina.url}"
    for i in range(elementos.count()):
        e = elementos.nth(i)
        if not e.is_visible():
            continue
        estilo = e.evaluate(
            "e => { const c = getComputedStyle(e); return [parseFloat(c.borderTopLeftRadius),"
            " e.getBoundingClientRect().height, c.textDecorationLine]; }"
        )
        assert estilo[0] >= 14, f"{selector}: sin esquinas de botón en {pagina.url}"
        assert estilo[1] >= 34, f"{selector}: muy bajo para tocar ({estilo[1]} px)"
        assert "underline" not in estilo[2], f"{selector}: subrayado"
        e.hover(force=True)
        assert "underline" not in e.evaluate("e => getComputedStyle(e).textDecorationLine")
        assert e.evaluate("e => getComputedStyle(e, '::after').content") in ("none", "normal", '""')


def _ir(pagina, live_server, ruta):
    pagina.set_viewport_size({"width": 1280, "height": 900})
    pagina.goto(live_server.url + ruta)
    pagina.wait_for_load_state("networkidle")
    pagina.add_style_tag(content=".asistente-widget{display:none !important}")


def test_portada(page, live_server, datos):
    _ir(page, live_server, "/")
    _como_boton(page, ".hero-acciones a:has-text('Cómo funciona')")


def test_listado_de_productos(page, live_server, datos):
    _ir(page, live_server, "/productos/")
    _como_boton(page, ".tp-mapa")
    _como_boton(page, ".tarjeta-precio a.ir")


def test_comparacion_de_un_producto(page, live_server, datos):
    _ir(page, live_server, f"/productos/{datos[0].pk}/")
    _como_boton(page, ".tp-mapa")


def test_directorio(page, live_server, datos):
    _ir(page, live_server, "/establecimientos/")
    _como_boton(page, ".tp-mapa")
    _como_boton(page, ".tarjeta-enlace .ir")


def test_pagina_de_un_comercio(page, live_server, datos):
    _ir(page, live_server, f"/tiendas/{datos[1].pk}/")
    _como_boton(page, ".tp-mapa")
    _como_boton(page, ".tarjeta-precio a.ir")


_CONTRASTE = """e => {
  const lum = c => { const v = c.match(/[\\d.]+/g).slice(0, 3).map(Number).map(x => { x /= 255;
    return x <= .03928 ? x / 12.92 : ((x + .055) / 1.055) ** 2.4; });
    return .2126 * v[0] + .7152 * v[1] + .0722 * v[2]; };
  const s = getComputedStyle(e), a = lum(s.color), b = lum(s.backgroundColor);
  return (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
}"""


@pytest.mark.parametrize("tema", ["light", "dark"])
def test_directorio_boton_legible_al_pasar_por_la_tarjeta(page, live_server, datos, tema):
    page.add_init_script(f"localStorage.setItem('ahorrapues-tema', '{tema}')")
    _ir(page, live_server, "/establecimientos/")
    tarjeta = page.locator(".tarjeta-enlace").first
    tarjeta.hover(position={"x": 8, "y": 8})
    ir = tarjeta.locator(".ir")
    assert ir.evaluate(_CONTRASTE) >= 4.5, "«Ver sus precios» pierde contraste con el mouse encima"
    assert ir.evaluate("e => getComputedStyle(e).cursor") == "pointer"
    assert tarjeta.locator(".tp-mapa").evaluate("e => getComputedStyle(e).cursor") == "pointer"
