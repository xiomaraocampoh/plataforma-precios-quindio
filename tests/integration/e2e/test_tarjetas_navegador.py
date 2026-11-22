"""Tarjetas de precio y registro en un navegador real (RF-16, M-03).

Cálculo en vivo de «Equivale a $X por kg», contraste ≥ 4.5:1 (1.4.3), objetivos ≥ 24 px (2.5.8)
y sin desplazamiento horizontal (1.4.10), en móvil, escritorio y modo oscuro.
Con GUARDAR_EVIDENCIAS=1 guarda capturas en docs/calidad/evidencias/tarjetas/.
"""

import os
from decimal import Decimal
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse
from playwright.sync_api import expect

from apps.catalogo.models import Marca
from apps.establecimientos.models import Establecimiento
from apps.precios import services
from apps.precios.models import ReportePrecio

pytestmark = [pytest.mark.integration, pytest.mark.e2e]

EVIDENCIAS = Path(settings.BASE_DIR) / "docs" / "calidad" / "evidencias" / "tarjetas"
MOVIL = {"width": 390, "height": 844}
ESCRITORIO = {"width": 1280, "height": 900}
_LINEAS_JS = Path(__file__).with_name("contraste.js").read_text(encoding="utf-8").splitlines()
JS = "\n".join(li for li in _LINEAS_JS if not li.startswith("//")).strip().rstrip(";")
OBJETIVOS_JS = (
    "() => [...document.querySelectorAll("
    "'.tarjeta-precio a, .tarjeta-precio button, .tarjeta-precio summary')]"
    ".filter(el => el.getBoundingClientRect().width > 1)"
    ".filter(el => { const r = el.getBoundingClientRect(); return r.width < 24 || r.height < 24; })"
    ".map(el => el.textContent.trim().slice(0, 40))"
)


@pytest.fixture
def datos(reportante, arroz, tiendas):
    prod, p500, p1kg = arroz
    prod.marca = Marca.objects.create(nombre="Diana")
    prod.save()
    rosa, super_ = tiendas
    mini = Establecimiento.objects.create(
        nombre="Minimercado La Esquina",
        tipo="minimercado",
        direccion="Cra 19 # 14-55",
        barrio="Granada",
        municipio="Calarcá",
    )
    for presentacion, local, precio in [
        (p1kg, super_, 8000),
        (p500, rosa, 4500),
        (p500, mini, 4300),
    ]:
        services.registrar_reporte(
            autor=reportante,
            presentacion_id=presentacion.pk,
            establecimiento_id=local.pk,
            precio=Decimal(precio),
        )
    return prod, p500, p1kg


@pytest.fixture
def pagina(live_server, context, client, django_user_model):
    """Sesión de otra persona (no la autora): ve «Sigue igual» y «Denunciar»."""
    vecina = django_user_model.objects.create_user(
        username="vecina", password=None, acepto_tratamiento_datos=True
    )
    client.force_login(vecina)
    context.add_cookies(
        [{"name": "sessionid", "value": client.cookies["sessionid"].value, "url": live_server.url}]
    )
    pagina = context.new_page()
    pagina.set_default_timeout(10_000)
    return pagina


def _guardar(pagina, nombre: str) -> None:
    if os.environ.get("GUARDAR_EVIDENCIAS") == "1":
        EVIDENCIAS.mkdir(parents=True, exist_ok=True)
        pagina.screenshot(path=str(EVIDENCIAS / f"{nombre}.png"), full_page=True)


def _verificar_accesibilidad(pagina, ancho: int) -> None:
    assert pagina.evaluate(JS) == []  # 1.4.3
    assert pagina.evaluate(OBJETIVOS_JS) == []  # 2.5.8
    assert pagina.evaluate("() => document.documentElement.scrollWidth") <= ancho  # 1.4.10


@pytest.mark.parametrize(
    ("nombre", "tamano", "esquema"),
    [
        ("comparacion-movil-claro", MOVIL, "light"),
        ("comparacion-escritorio-claro", ESCRITORIO, "light"),
        ("comparacion-movil-oscuro", MOVIL, "dark"),
        ("comparacion-escritorio-oscuro", ESCRITORIO, "dark"),
    ],
)
def test_tarjetas_de_la_comparacion(pagina, live_server, datos, nombre, tamano, esquema):
    pagina.set_viewport_size(tamano)
    pagina.emulate_media(color_scheme=esquema)
    pagina.goto(live_server.url + reverse("comparacion:comparar", args=[datos[0].pk]))
    primera = pagina.locator(".tarjeta-precio").first
    expect(primera).to_contain_text("$8.000 por kg")
    expect(primera).to_contain_text("para comparar empaques de distinto tamaño")
    expect(primera).to_contain_text("Ver en el mapa")
    expect(primera).to_contain_text("Confianza media")
    expect(primera.get_by_role("button", name="Sigue igual")).to_be_visible()
    _verificar_accesibilidad(pagina, tamano["width"])
    _guardar(pagina, nombre)


@pytest.mark.parametrize("esquema", ["light", "dark"])
def test_tarjetas_del_listado(pagina, live_server, datos, esquema):
    pagina.set_viewport_size(MOVIL)
    pagina.emulate_media(color_scheme=esquema)
    pagina.goto(live_server.url + reverse("comparacion:productos"))
    tarjeta = pagina.locator(".tarjeta-precio").first
    expect(tarjeta).to_contain_text("$8.000 por kg")
    expect(tarjeta).to_contain_text("Ver todos los precios")
    _verificar_accesibilidad(pagina, MOVIL["width"])
    _guardar(pagina, f"productos-movil-{'oscuro' if esquema == 'dark' else 'claro'}")


def test_registro_calcula_en_vivo_el_precio_por_unidad(pagina, live_server, datos):
    producto, p500, p1kg = datos
    pagina.set_viewport_size(MOVIL)
    pagina.goto(f"{live_server.url}{reverse('precios:registrar')}?producto={producto.pk}")
    precio = pagina.get_by_label("Precio total del empaque ($)")
    salida = pagina.locator("#precio-equivale")
    pagina.check(f"input[name=presentacion][value='{p500.pk}']")
    precio.fill("4500")
    expect(salida).to_have_text("Equivale a $9.000 por kg")
    pagina.check(f"input[name=presentacion][value='{p1kg.pk}']")
    expect(salida).to_have_text("Equivale a $4.500 por kg")
    _guardar(pagina, "registro-equivale-movil")
    precio.fill("")
    expect(salida).to_have_text("")


# ---------- registrar con pocos toques (EC-01, PUX-01) ----------

TODOS_LOS_OBJETIVOS_JS = (
    "() => [...document.querySelectorAll("
    "'main a, main button, main summary, main select, main input:not([type=hidden])')]"
    ".filter(el => { const r = el.getBoundingClientRect(); return r.width > 1 && r.height > 1; })"
    ".filter(el => { const r = el.getBoundingClientRect(); return r.width < 24 || r.height < 24; })"
    ".map(el => (el.getAttribute('name') || el.textContent || el.tagName).trim().slice(0, 40))"
)


def _accesible_en_toda_la_pagina(pagina, ancho: int) -> None:
    assert pagina.evaluate(JS) == []  # 1.4.3 contraste
    assert pagina.evaluate(TODOS_LOS_OBJETIVOS_JS) == []  # 2.5.8 objetivos ≥ 24 px
    assert pagina.evaluate("() => document.documentElement.scrollWidth") <= ancho  # 1.4.10


@pytest.mark.parametrize("esquema", ["light", "dark"])
def test_registro_paso_a_paso_es_accesible_en_claro_y_oscuro(pagina, live_server, datos, esquema):
    producto, p500, _ = datos
    pagina.set_viewport_size(MOVIL)
    pagina.emulate_media(color_scheme=esquema)
    pagina.goto(live_server.url + reverse("precios:registrar"))
    expect(pagina.get_by_label("¿Qué producto?")).to_be_visible()
    _accesible_en_toda_la_pagina(pagina, MOVIL["width"])
    pagina.get_by_label("¿Qué producto?").fill("arro")  # resultados en vivo, sin recargar
    expect(pagina.get_by_role("link", name="Arroz blanco").first).to_be_visible()
    pagina.get_by_role("link", name="Arroz blanco").first.click()
    expect(pagina.get_by_role("group", name="Presentación")).to_be_visible()
    pagina.check(f"input[name=presentacion][value='{p500.pk}']")
    _accesible_en_toda_la_pagina(pagina, MOVIL["width"])
    _guardar(pagina, f"registro-paso2-{'oscuro' if esquema == 'dark' else 'claro'}")


def test_desde_la_comparacion_se_registra_con_dos_toques(pagina, live_server, datos):
    """«Registrar precio aquí» (todo precargado) y «Guardar»: solo se escribe el precio."""
    producto, p500, _ = datos
    antes = ReportePrecio.objects.count()
    pagina.set_viewport_size(MOVIL)
    pagina.goto(live_server.url + reverse("comparacion:comparar", args=[producto.pk]))
    pagina.get_by_role("link", name="Registrar precio aquí").first.click()  # toque 1
    expect(pagina.locator("input[name=presentacion]:checked")).to_have_count(1)
    expect(pagina.locator("input[name=precio]")).to_be_focused()  # el cursor ya está en el precio
    pagina.keyboard.type("4200")
    pagina.get_by_role("button", name="Guardar precio").click()  # toque 2
    expect(pagina.locator("[data-registro-guardado]")).to_contain_text("ya está publicado")
    assert ReportePrecio.objects.count() == antes + 1
    ultimo = ReportePrecio.objects.order_by("-pk").first()
    assert ultimo.precio == Decimal("4200")
