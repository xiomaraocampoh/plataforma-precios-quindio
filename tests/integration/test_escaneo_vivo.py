"""Escáner en vivo (ADR-0026): POST /escanear/fotograma/, su resultado y el registro prellenado.

El reconocedor es falso: nunca se sale a la red. Se verifica privacidad (M-15), autenticidad de la
escritura (M-13), protección contra errores de unidad (M-02), pocos toques (M-01) y neutralidad
(EC-06).
"""

import logging
from decimal import Decimal
from urllib.parse import parse_qs, urlparse

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.establecimientos.models import Establecimiento
from apps.integraciones import services as integraciones
from apps.integraciones.clients.vision import ReconocimientoNoDisponibleError
from apps.integraciones.domain.escaneo import ResultadoEscaneo, TipoEscaneo
from apps.integraciones.domain.etiqueta import EtiquetaPrecio
from apps.integraciones.domain.reconocimiento import PistaProducto
from apps.precios import services as precios
from apps.precios.models import ReportePrecio

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

URL = reverse("comparacion:escanear_fotograma")
REGISTRAR = reverse("precios:registrar")
JPEG = b"\xff\xd8\xff\xe0" + b"fotograma"
GTIN = "7702001023011"


def _etiqueta(**cambios):
    base = {
        "precio": Decimal("4350"),
        "nombre": "Arroz blanco",
        "marca": "",
        "cantidad": Decimal("500"),
        "unidad": "g",
        "confianza": "alta",
    }
    return EtiquetaPrecio(**{**base, **cambios})


def _pista(nombre="Arroz blanco", codigo="", cantidad="500", unidad="g", marca=""):
    return PistaProducto(nombre, marca, cantidad, unidad, codigo, "alta")


def _res_etiqueta(**cambios):
    e = _etiqueta(**cambios)
    pista = _pista(e.nombre, e.codigo_barras, str(e.cantidad or ""), e.unidad or "", e.marca)
    return ResultadoEscaneo(TipoEscaneo.ETIQUETA, pista=pista, etiqueta=e)


class Falso:
    def __init__(self, resultado=None, error=None):
        self.resultado, self.error, self.llamadas = resultado, error, 0

    def escanear(self, imagen, tipo):
        self.llamadas += 1
        if self.error:
            raise self.error
        return self.resultado


@pytest.fixture(autouse=True)
def _activo(settings):
    settings.INTEGRACIONES = {
        **settings.INTEGRACIONES,
        "ANTHROPIC_API_KEY": "clave-de-prueba",
        "ESCANEO_VIVO_ACTIVO": True,
        "RECONOCIMIENTOS_POR_HORA": 3,
        "RECONOCIMIENTOS_ANONIMO_POR_HORA": 2,
        "RECONOCIMIENTOS_POR_DIA_TOTAL": 50,
    }


@pytest.fixture
def falso(monkeypatch):
    f = Falso(ResultadoEscaneo.nada())
    monkeypatch.setattr(integraciones, "_crear_reconocedor", lambda: f)
    return f


@pytest.fixture
def arroz_gtin(arroz):
    prod, p500, p1kg = arroz
    p500.codigo_barras = GTIN
    p500.save()
    return prod, p500, p1kg


def _enviar(client, contenido=JPEG):
    return client.post(URL, {"fotograma": SimpleUploadedFile("f.jpg", contenido)})


def _enlace_registrar(html: str) -> dict:
    inicio = html.index(f'href="{REGISTRAR}?')
    url = html[inicio + 6 : html.index('"', inicio + 6)].replace("&amp;", "&")
    return {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}


# ───────────── activación ─────────────


def test_apagado_por_defecto_no_existe(client, settings, falso):
    settings.INTEGRACIONES = {**settings.INTEGRACIONES, "ESCANEO_VIVO_ACTIVO": False}
    assert _enviar(client).status_code == 404 and falso.llamadas == 0


def test_sin_clave_no_existe(client, settings, falso):
    settings.INTEGRACIONES = {**settings.INTEGRACIONES, "ANTHROPIC_API_KEY": ""}
    assert _enviar(client).status_code == 404 and falso.llamadas == 0


def test_solo_post(client, falso):
    assert client.get(URL).status_code == 405


def test_la_portada_ofrece_el_modo_en_vivo_solo_si_esta_activo(client, settings, db):
    assert 'data-vivo-url="' + URL in client.get("/").content.decode()
    settings.INTEGRACIONES = {**settings.INTEGRACIONES, "ESCANEO_VIVO_ACTIVO": False}
    html = client.get("/").content.decode()
    assert "data-vivo-url" not in html
    assert "data-escanear" in html  # el código de barras sigue


# ───────────── resultados ─────────────


def test_nada_reconocido_responde_sin_contenido(client, falso):
    r = _enviar(client)
    assert r.status_code == 204 and r.content == b""


def test_producto_por_codigo_abre_su_comparacion(client, falso, arroz_gtin):
    prod = arroz_gtin[0]
    falso.resultado = ResultadoEscaneo(TipoEscaneo.PRODUCTO, pista=_pista("", GTIN, "", ""))
    html = _enviar(client).content.decode()
    assert reverse("comparacion:comparar", args=[prod.pk]) in html
    assert "Ver comparación" in html and "Arroz blanco" in html
    assert 'data-escaneo="producto"' in html


def test_producto_por_nombre(client, falso, arroz):
    falso.resultado = ResultadoEscaneo(TipoEscaneo.PRODUCTO, pista=_pista())
    html = _enviar(client).content.decode()
    assert reverse("comparacion:comparar", args=[arroz[0].pk]) in html


def test_producto_fuera_del_catalogo_ofrece_solicitarlo_prellenado(client, falso, db):
    falso.resultado = ResultadoEscaneo(
        TipoEscaneo.PRODUCTO, pista=_pista("Quinua", GTIN, "250", "g", "Andina")
    )
    html = _enviar(client).content.decode()
    assert "Solicitar este producto" in html
    for dato in (
        "nombre=Quinua",
        "marca=Andina",
        "cantidad=250",
        "unidad=g",
        f"codigo_barras={GTIN}",
    ):
        assert dato in html


def test_etiqueta_muestra_precio_y_precio_por_unidad_calculado(client, falso, arroz, tiendas):
    falso.resultado = _res_etiqueta(
        precio_por_unidad_impreso=Decimal("8.70"), unidad_impresa="g", consistente=True
    )
    html = _enviar(client).content.decode()
    assert 'data-escaneo="etiqueta"' in html
    assert "$4.350" in html
    assert "$8.700 por kg" in html  # calculado con precio_por_unidad (M-02), no el impreso
    assert "Impreso en la etiqueta" in html
    assert "Registrar este precio" in html and "Ver comparación" in html


def test_etiqueta_en_promocion_se_marca_y_no_cambia_el_orden(
    client, falso, arroz, tiendas, reportante
):  # EC-06
    _, p500, _ = arroz
    falso.resultado = _res_etiqueta(es_promocion=True, precio_anterior=Decimal("5200"))
    html = _enviar(client).content.decode()
    assert "Promoción" in html and "$5.200" in html
    # El registro desde la etiqueta no guarda ni usa la promoción para ordenar (EC-06)
    barato = precios.registrar_reporte(
        autor=reportante,
        presentacion_id=p500.pk,
        establecimiento_id=tiendas[0].pk,
        precio=Decimal("4000"),
    )
    promo = precios.registrar_reporte(
        autor=reportante,
        presentacion_id=p500.pk,
        establecimiento_id=tiendas[1].pk,
        precio=Decimal("4350"),
        origen=ReportePrecio.Origen.ETIQUETA,
    )
    filas = client.get(reverse("api-comparacion", args=[arroz[0].pk])).json()["resultados"]
    assert [f["establecimiento_id"] for f in filas] == [
        barato.establecimiento_id,
        promo.establecimiento_id,
    ]


def test_etiqueta_propone_la_tienda_del_directorio(client, falso, arroz, tiendas):
    falso.resultado = _res_etiqueta(establecimiento_texto="SÚPER QUINDÍO")
    datos = _enlace_registrar(_enviar(client).content.decode())
    assert datos["establecimiento"] == str(tiendas[1].pk)
    assert datos["precio"] == "4350" and datos["origen"] == "etiqueta"
    assert datos["producto"] == str(arroz[0].pk) and datos["presentacion"] == str(arroz[1].pk)


def test_tienda_desconocida_usa_la_ultima_y_no_crea_ninguna(
    client, falso, arroz, tiendas, reportante
):
    precios.registrar_reporte(
        autor=reportante,
        presentacion_id=arroz[2].pk,
        establecimiento_id=tiendas[0].pk,
        precio=Decimal("8000"),
    )
    client.force_login(reportante)
    falso.resultado = _res_etiqueta(establecimiento_texto="Autoservicio El Paisa")
    antes = Establecimiento.objects.count()
    html = _enviar(client).content.decode()
    assert Establecimiento.objects.count() == antes  # nunca se crea una tienda sola
    assert _enlace_registrar(html)["establecimiento"] == str(tiendas[0].pk)
    assert "Sugerir este establecimiento" in html
    assert reverse("establecimientos:sugerir") + "?nombre=Autoservicio" in html


def test_etiqueta_de_producto_fuera_del_catalogo(client, falso, db):
    falso.resultado = _res_etiqueta(nombre="Quinua", codigo_barras=GTIN)
    html = _enviar(client).content.decode()
    assert "Solicitar este producto" in html and "Registrar este precio" not in html


def test_presentacion_distinta_no_se_preselecciona(client, falso, arroz, tiendas):  # M-02
    falso.resultado = _res_etiqueta(cantidad=Decimal("250"))
    datos = _enlace_registrar(_enviar(client).content.decode())
    assert "presentacion" not in datos  # la persona elige la presentación: no se adivina


# ───────────── errores y topes ─────────────


def test_imagen_invalida(client, falso):
    r = _enviar(client, b"%PDF-1.7")
    assert r.status_code == 400 and falso.llamadas == 0


def test_sin_fotograma(client, falso):
    assert client.post(URL).status_code == 400


def test_timeout_no_rompe_el_escaner(client, falso):
    falso.error = ReconocimientoNoDisponibleError("APITimeoutError")
    r = _enviar(client)
    assert r.status_code == 503 and "código de barras" in r.content.decode()


def test_tope_por_hora_compartido_con_la_foto(client, falso):  # M-16
    _enviar(client)
    _enviar(client)
    r = _enviar(client)
    assert r.status_code == 429 and falso.llamadas == 2


def test_throttle_scope_propio(client, falso, monkeypatch):  # M-13
    from rest_framework.throttling import ScopedRateThrottle

    monkeypatch.setitem(ScopedRateThrottle.THROTTLE_RATES, "escaneo", "1/min")
    _enviar(client)
    r = _enviar(client)
    assert r.status_code == 429 and falso.llamadas == 1


def test_la_imagen_no_se_registra_en_los_logs(client, falso, reportante, caplog):  # M-15
    client.force_login(reportante)
    falso.resultado = _res_etiqueta()
    with caplog.at_level(logging.DEBUG):
        _enviar(client)
    texto = " ".join(r.getMessage() for r in caplog.records)
    assert "etiqueta" in texto  # el resultado sí
    assert "reportante1" not in texto and "127.0.0.1" not in texto and "fotograma" not in texto


# ───────────── registrar desde la etiqueta ─────────────


def test_registrar_sin_sesion_pide_ingresar_y_conserva_los_datos(client, arroz, tiendas):  # M-13
    params = f"producto={arroz[0].pk}&presentacion={arroz[1].pk}&precio=4350&origen=etiqueta"
    r = client.get(f"{REGISTRAR}?{params}")
    assert r.status_code == 302
    assert "precio%3D4350" in r["Location"] or "precio=4350" in r["Location"]


def test_registro_llega_prellenado(client, reportante, arroz, tiendas):  # M-01
    client.force_login(reportante)
    html = client.get(
        REGISTRAR,
        {
            "producto": arroz[0].pk,
            "presentacion": arroz[1].pk,
            "establecimiento": tiendas[1].pk,
            "precio": "4350",
            "origen": "etiqueta",
        },
    ).content.decode()
    assert 'value="4350"' in html
    assert 'name="origen" value="etiqueta"' in html
    assert f'value="{arroz[1].pk}"' in html and "checked" in html


@pytest.mark.parametrize("precio", ["-5", "abc", "0", "99999999999"])
def test_un_precio_raro_en_la_direccion_no_se_prellena(client, reportante, arroz, precio):  # M-02
    client.force_login(reportante)
    html = client.get(REGISTRAR, {"producto": arroz[0].pk, "precio": precio}).content.decode()
    assert f'value="{precio}"' not in html


def test_confirmar_guarda_el_origen_por_el_servicio_de_siempre(client, reportante, arroz, tiendas):
    client.force_login(reportante)
    r = client.post(
        f"{REGISTRAR}?producto={arroz[0].pk}",
        {
            "presentacion": arroz[1].pk,
            "establecimiento": tiendas[0].pk,
            "precio": "4350",
            "origen": "etiqueta",
        },
    )
    assert r.status_code == 200
    reporte = ReportePrecio.objects.get()
    assert reporte.origen == ReportePrecio.Origen.ETIQUETA and reporte.autor == reportante


def test_origen_desconocido_queda_manual(client, reportante, arroz, tiendas):
    client.force_login(reportante)
    client.post(
        f"{REGISTRAR}?producto={arroz[0].pk}",
        {
            "presentacion": arroz[1].pk,
            "establecimiento": tiendas[0].pk,
            "precio": "4350",
            "origen": "inventado",
        },
    )
    assert ReportePrecio.objects.get().origen == ReportePrecio.Origen.MANUAL


def test_el_origen_no_sale_en_la_api_publica(api, reportante, arroz, tiendas):  # M-15
    precios.registrar_reporte(
        autor=reportante,
        presentacion_id=arroz[1].pk,
        establecimiento_id=tiendas[0].pk,
        precio=Decimal("4350"),
        origen=ReportePrecio.Origen.ETIQUETA,
    )
    texto = api.get(reverse("api-comparacion", args=[arroz[0].pk])).content.decode()
    assert "origen" not in texto and "etiqueta" not in texto and "reportante1" not in texto
