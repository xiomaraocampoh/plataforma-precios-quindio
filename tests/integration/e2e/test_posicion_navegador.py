"""Al paginar o enviar un formulario la página no vuelve arriba: conserva la posición (RF-19)."""

import pytest

from apps.catalogo.domain.duplicados import normalizar_nombre
from apps.catalogo.models import Categoria, Producto

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def muchos_productos():
    categoria = Categoria.objects.create(nombre="Granos")
    for i in range(60):
        nombre = f"Producto {i:02d}"
        Producto.objects.create(
            nombre=nombre, nombre_normalizado=normalizar_nombre(nombre), categoria=categoria
        )


def _y(pagina):
    return pagina.evaluate("window.scrollY")


def test_paginar_no_devuelve_al_inicio(page, live_server, muchos_productos):
    page.set_viewport_size({"width": 1280, "height": 600})
    page.goto(live_server.url + "/productos/")
    page.wait_for_load_state("networkidle")
    page.add_style_tag(content=".asistente-widget{display:none !important}")
    page.evaluate("window.scrollTo(0, 700)")
    antes = _y(page)
    assert antes > 0
    page.get_by_role("link", name="Siguiente").click()
    page.wait_for_url("**pagina=2")
    page.wait_for_load_state("networkidle")
    assert abs(_y(page) - antes) <= 2


def test_otra_pagina_empieza_arriba(page, live_server, muchos_productos):
    page.set_viewport_size({"width": 1280, "height": 600})
    page.goto(live_server.url + "/productos/")
    page.evaluate("window.scrollTo(0, 700)")
    page.goto(live_server.url + "/establecimientos/")
    assert _y(page) == 0
