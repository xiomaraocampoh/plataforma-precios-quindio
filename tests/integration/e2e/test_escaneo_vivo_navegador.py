"""Escáner en vivo en un navegador real con cámara falsa (ADR-0026, M-01, M-03).

Chromium recibe un video corto y quieto de una etiqueta de precio
(--use-file-for-fake-video-capture) y el reconocedor del servidor es falso (sin red). Se verifica
que la hoja aparece SIN tocar «Tomar foto», que el registro llega prellenado y se confirma con un
toque, y la accesibilidad de la hoja:
contraste (1.4.3), objetivos ≥ 24 px (2.5.8), aria-live y foco al abrirla.
Con GUARDAR_EVIDENCIAS=1 guarda capturas en docs/calidad/evidencias/escaneo/.
"""

import os
from decimal import Decimal
from pathlib import Path

import pytest
from django.conf import settings
from playwright.sync_api import expect

from apps.integraciones import services as integraciones
from apps.integraciones.domain.escaneo import ResultadoEscaneo, TipoEscaneo
from apps.integraciones.domain.etiqueta import EtiquetaPrecio
from apps.integraciones.domain.reconocimiento import PistaProducto
from apps.precios.models import ReportePrecio

pytestmark = [pytest.mark.integration, pytest.mark.e2e]

EVIDENCIAS = Path(settings.BASE_DIR) / "docs" / "calidad" / "evidencias" / "escaneo"
MOVIL = {"width": 390, "height": 844}
_LINEAS_JS = Path(__file__).with_name("contraste.js").read_text(encoding="utf-8").splitlines()
CONTRASTE_JS = "\n".join(li for li in _LINEAS_JS if not li.startswith("//")).strip().rstrip(";")
OBJETIVOS_JS = (
    "(raiz) => [...document.querySelectorAll(raiz + ' a, ' + raiz + ' button')]"
    ".filter(el => el.getBoundingClientRect().width > 1)"
    ".filter(el => { const r = el.getBoundingClientRect(); return r.width < 24 || r.height < 24; })"
    ".map(el => el.textContent.trim().slice(0, 40))"
)


def _video_de_etiqueta(ruta: Path, ancho: int = 320, alto: int = 240, cuadros: int = 20) -> Path:
    """Un .y4m quieto con una «etiqueta» de alto contraste: fondo claro, borde y bloques oscuros
    (precio grande y renglones de texto). Sin dependencias: se escribe el YUV 4:2:0 a mano."""
    luz = bytearray([235]) * (ancho * alto)

    def bloque(x0, y0, x1, y1):
        for y in range(y0, y1):
            luz[y * ancho + x0 : y * ancho + x1] = bytes([16]) * (x1 - x0)

    bloque(20, 20, 300, 26)  # borde superior
    bloque(20, 214, 300, 220)  # borde inferior
    for i, x in enumerate(range(40, 280, 40)):  # «$4.350» en bloques grandes
        bloque(x, 60, x + 28, 130 if i % 2 else 120)
    for y in (150, 170, 190):  # renglones: nombre, cantidad, precio por unidad
        bloque(40, y, 260 - (y - 150), y + 8)
    croma = bytes([128]) * ((ancho // 2) * (alto // 2))
    with ruta.open("wb") as video:
        video.write(f"YUV4MPEG2 W{ancho} H{alto} F10:1 Ip A1:1 C420jpeg\n".encode())
        for _ in range(cuadros):
            video.write(b"FRAME\n" + bytes(luz) + croma + croma)
    return ruta


class Falso:
    def __init__(self, resultado):
        self.resultado, self.llamadas = resultado, 0

    def escanear(self, imagen, tipo):
        assert tipo == "image/jpeg"  # el navegador recodifica a JPEG antes de enviar
        self.llamadas += 1
        return self.resultado


@pytest.fixture
def falso(monkeypatch, settings, arroz):
    settings.INTEGRACIONES = {
        **settings.INTEGRACIONES,
        "ANTHROPIC_API_KEY": "clave-de-prueba",
        "ESCANEO_VIVO_ACTIVO": True,
        "ESCANEO_INTERVALO_MS": 300,
    }
    etiqueta = EtiquetaPrecio(
        precio=Decimal("4350"),
        nombre="Arroz blanco",
        marca="",
        cantidad=Decimal("500"),
        unidad="g",
        es_promocion=True,
        precio_anterior=Decimal("5200"),
        establecimiento_texto="Súper Quindío",
        confianza="alta",
    )
    pista = PistaProducto("Arroz blanco", "", "500", "g", "", "alta")
    f = Falso(ResultadoEscaneo(TipoEscaneo.ETIQUETA, pista=pista, etiqueta=etiqueta))
    monkeypatch.setattr(integraciones, "_crear_reconocedor", lambda: f)
    return f


@pytest.fixture
def esquema():
    return "light"


@pytest.fixture
def pagina(playwright, live_server, client, reportante, tmp_path, esquema):
    video = _video_de_etiqueta(tmp_path / "etiqueta.y4m")
    navegador = playwright.chromium.launch(
        args=[
            "--use-fake-ui-for-media-stream",
            "--use-fake-device-for-media-stream",
            f"--use-file-for-fake-video-capture={video}",
        ]
    )
    contexto = navegador.new_context(viewport=MOVIL, permissions=["camera"], color_scheme=esquema)
    client.force_login(reportante)
    contexto.add_cookies(
        [{"name": "sessionid", "value": client.cookies["sessionid"].value, "url": live_server.url}]
    )
    p = contexto.new_page()
    p.set_default_timeout(15_000)
    yield p
    contexto.close()
    navegador.close()


def _evidencia(pagina, nombre: str) -> None:
    if os.environ.get("GUARDAR_EVIDENCIAS") == "1":
        EVIDENCIAS.mkdir(parents=True, exist_ok=True)
        pagina.screenshot(path=str(EVIDENCIAS / f"{nombre}.png"))


@pytest.mark.parametrize("esquema", ["light", "dark"])
def test_la_hoja_aparece_sola_y_el_registro_llega_prellenado(
    pagina, live_server, falso, arroz, tiendas, reportante, esquema
):  # M-01
    _, p500, _ = arroz
    pagina.goto(live_server.url + "/")
    pagina.locator("[data-escanear]").click()
    hoja = pagina.locator("[data-hoja]")
    expect(hoja).to_be_visible()  # sin pulsar «Tomar foto»: el cuadro quieto se envió solo
    assert falso.llamadas >= 1
    expect(hoja.locator(".esc-precio")).to_contain_text("$4.350")
    expect(hoja.locator(".esc-promo")).to_have_text("Promoción")  # EC-06: solo una etiqueta
    expect(hoja).to_contain_text("Súper Quindío")
    _evidencia(pagina, f"hoja-etiqueta-movil-{esquema}")

    # Accesibilidad de la hoja (M-03)
    assert pagina.locator("[data-resultado]").get_attribute("aria-live") == "polite"
    assert pagina.evaluate("document.activeElement.hasAttribute('data-foco')")  # foco al abrirla
    assert pagina.evaluate(CONTRASTE_JS, "[data-hoja]") == []  # 1.4.3
    assert pagina.evaluate(OBJETIVOS_JS, "[data-hoja]") == []  # 2.5.8
    assert pagina.evaluate(OBJETIVOS_JS, ".esc-controles") == []  # 2.5.8

    # El escaneo queda en pausa mientras la hoja está abierta: no se gasta cupo de más
    enviados = falso.llamadas
    pagina.wait_for_timeout(1200)
    assert falso.llamadas == enviados

    # «Registrar este precio» abre el registro rápido con todo prellenado (PR #28)
    hoja.get_by_role("link", name="Registrar este precio").click()
    expect(pagina.locator("input[name=precio]")).to_have_value("4350")
    expect(pagina.locator(f"input[name=presentacion][value='{p500.pk}']")).to_be_checked()
    expect(pagina.locator("select[name=establecimiento]")).to_have_value(str(tiendas[1].pk))
    expect(pagina.get_by_text("Leímos estos datos de la etiqueta")).to_be_visible()
    _evidencia(pagina, f"registro-prellenado-movil-{esquema}")

    pagina.get_by_role("button", name="Guardar precio").click()  # un toque para confirmar
    expect(pagina.get_by_role("status").first).to_be_attached()
    pagina.wait_for_function("() => !document.querySelector('input[name=precio]')")
    reporte = ReportePrecio.objects.get()
    assert reporte.precio == Decimal("4350") and reporte.autor == reportante
    assert reporte.origen == ReportePrecio.Origen.ETIQUETA
    assert reporte.establecimiento_id == tiendas[1].pk


def test_pausar_escaneo_es_un_boton_conmutable(pagina, live_server, falso):
    pagina.goto(live_server.url + "/")
    pagina.locator("[data-escanear]").click()
    pausar = pagina.get_by_role("button", name="Pausar escaneo")
    expect(pausar).to_have_attribute("aria-pressed", "false")
    pausar.click()
    expect(pausar).to_have_attribute("aria-pressed", "true")
    enviados = falso.llamadas
    pagina.wait_for_timeout(1500)
    assert falso.llamadas == enviados  # en pausa no se envía nada
    expect(pagina.locator("[data-hoja]")).to_be_hidden()
