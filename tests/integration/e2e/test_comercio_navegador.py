"""Flujo del comercio en un navegador real (RF-C01 a RF-C05, ADR-015, ADR-018, M-03).

Crear el perfil → un moderador lo verifica → el comercio publica su precio → la comparación lo
muestra como «Oficial». En cada pantalla: contraste ≥ 4.5:1 (1.4.3), objetivos ≥ 24 px (2.5.8) y
sin desplazamiento horizontal (1.4.10), en claro y oscuro.
"""

from pathlib import Path

import pytest
from django.urls import reverse
from playwright.sync_api import expect

from apps.comercios.models import DocumentoComercio, PerfilComercio, PrecioOficial
from tests.integration.comercios.pdf import CAMARA, RUT

pytestmark = [pytest.mark.integration, pytest.mark.e2e]

MOVIL = {"width": 390, "height": 844}
_LINEAS_JS = Path(__file__).with_name("contraste.js").read_text(encoding="utf-8").splitlines()
CONTRASTE_JS = "\n".join(li for li in _LINEAS_JS if not li.startswith("//")).strip().rstrip(";")
OBJETIVOS_JS = (
    "() => [...document.querySelectorAll("
    "'main a, main button, main summary, main select, main input:not([type=hidden])')]"
    ".filter(el => { const r = el.getBoundingClientRect(); return r.width > 1 && r.height > 1; })"
    ".filter(el => { const r = el.getBoundingClientRect(); return r.width < 24 || r.height < 24; })"
    ".map(el => (el.getAttribute('name') || el.textContent || el.tagName).trim().slice(0, 40))"
)


def _accesible(pagina, raiz: str = "main") -> None:
    assert pagina.evaluate(CONTRASTE_JS, raiz) == []  # 1.4.3
    assert pagina.evaluate(OBJETIVOS_JS) == []  # 2.5.8
    assert pagina.evaluate("() => document.documentElement.scrollWidth") <= MOVIL["width"]


def _entrar_como(context, client, live_server, usuario) -> None:
    client.force_login(usuario)  # incluye el segundo factor (tests/conftest.py)
    context.clear_cookies()
    context.add_cookies(
        [{"name": "sessionid", "value": client.cookies["sessionid"].value, "url": live_server.url}]
    )


@pytest.fixture
def moderador(django_user_model):
    return django_user_model.objects.create_user(
        username="mod_e2e", password=None, rol="moderador", is_staff=True
    )


@pytest.fixture
def duena(django_user_model):
    return django_user_model.objects.create_user(
        username="rosa_e2e", password=None, acepto_tratamiento_datos=True
    )


@pytest.mark.parametrize("esquema", ["light", "dark"])
def test_del_perfil_al_precio_oficial_en_la_comparacion(
    live_server, context, client, duena, moderador, arroz, tiendas, esquema
):
    producto, _, p1kg = arroz
    rosa = tiendas[0]
    pagina = context.new_page()
    pagina.set_default_timeout(10_000)
    pagina.set_viewport_size(MOVIL)
    pagina.emulate_media(color_scheme=esquema)

    # 1. La dueña crea el perfil (HTMX: la sección se reemplaza sin recargar)
    _entrar_como(context, client, live_server, duena)
    pagina.goto(live_server.url + reverse("comercios:inicio"))
    expect(pagina.get_by_role("heading", name="Crea el perfil de tu comercio")).to_be_visible()
    _accesible(pagina)
    pagina.get_by_label("Tu establecimiento").select_option(str(rosa.pk))
    pagina.get_by_label("Nombre de quien atiende el perfil").fill("Rosa")
    # ADR-0034: dos PDF; HTMX los envía en multipart (hx-encoding)
    pagina.get_by_label("Certificado de Cámara de Comercio (PDF)").set_input_files(
        {"name": "camara.pdf", "mimeType": "application/pdf", "buffer": CAMARA}
    )
    pagina.get_by_label("RUT (PDF)").set_input_files(
        {"name": "rut.pdf", "mimeType": "application/pdf", "buffer": RUT}
    )
    pagina.get_by_role("button", name="Enviar a verificación").click()
    expect(pagina.get_by_role("heading", name="Tu perfil está en revisión")).to_be_visible()
    expect(pagina.locator("#sec-perfil [role=status]")).to_contain_text("Moderación lo revisará")
    codigo = PerfilComercio.objects.get().codigo_verificacion
    expect(pagina.locator("#codigo-verificacion")).to_have_text(codigo)
    _accesible(pagina)

    # 2. Moderación lo verifica desde su bandeja
    _entrar_como(context, client, live_server, moderador)
    pagina.goto(live_server.url + reverse("comercios:verificacion"))
    expect(pagina.get_by_role("link", name="Ver Cámara de Comercio")).to_be_visible()
    expect(pagina.get_by_role("link", name="Ver RUT")).to_be_visible()
    _accesible(pagina)
    pagina.get_by_role("button", name="Verificar", exact=True).click()
    expect(pagina.locator(".lista-filas [role=status]")).to_have_text("Decisión registrada.")
    assert PerfilComercio.objects.get().verificado
    assert not DocumentoComercio.objects.filter(contenido__isnull=False).exists()  # minimización

    # 3. El comercio publica su precio oficial
    _entrar_como(context, client, live_server, duena)
    pagina.goto(live_server.url + reverse("comercios:inicio"))
    expect(pagina.get_by_role("heading", name="Precios oficiales")).to_be_visible()
    _accesible(pagina)
    pagina.get_by_label("Producto y presentación").select_option(str(p1kg.pk))
    pagina.get_by_label("Precio de venta (en pesos)").fill("4100")
    pagina.get_by_role("button", name="Publicar precio oficial").click()
    expect(pagina.locator("#sec-precios [role=status]")).to_contain_text("publicado por 30 días")
    expect(pagina.get_by_role("button", name="Mis precios siguen igual")).to_be_visible()
    assert PrecioOficial.objects.get().precio == 4100

    # 4. Cualquier persona lo ve como «Oficial» en la comparación, sin datos del comercio
    context.clear_cookies()
    pagina.goto(live_server.url + reverse("comparacion:comparar", args=[producto.pk]))
    tarjeta = pagina.locator(".tarjeta-precio").first
    expect(tarjeta).to_contain_text("Oficial")
    expect(tarjeta).to_contain_text("$4.100")
    expect(tarjeta).to_contain_text("Tienda Doña Rosa")
    expect(tarjeta).not_to_contain_text("NIT 900123456-7")
    _accesible(pagina, ".tarjeta-precio")
