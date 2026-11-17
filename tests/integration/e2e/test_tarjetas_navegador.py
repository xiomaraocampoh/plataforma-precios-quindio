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
    _, p500, p1kg = datos
    pagina.set_viewport_size(MOVIL)
    pagina.goto(live_server.url + reverse("precios:registrar"))
    precio = pagina.get_by_label("Precio total del empaque ($)")
    salida = pagina.locator("#precio-equivale")
    pagina.select_option("select[name=presentacion]", value=str(p500.pk))
    precio.fill("4500")
    expect(salida).to_have_text("Equivale a $9.000 por kg")
    pagina.select_option("select[name=presentacion]", value=str(p1kg.pk))
    expect(salida).to_have_text("Equivale a $4.500 por kg")
    _guardar(pagina, "registro-equivale-movil")
    precio.fill("")
    expect(salida).to_have_text("")
