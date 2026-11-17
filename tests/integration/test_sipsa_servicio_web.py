"""RF-07: precios de referencia SIPSA desde el servicio web SOAP del DANE (promediosSipsaCiudad).

Sin red: el cliente recibe un XML de ejemplo con la forma real de la respuesta.
"""

from datetime import date
from decimal import Decimal
from io import BytesIO, StringIO

import pytest
from django.core.management import CommandError, call_command

from apps.catalogo.models import Categoria, Presentacion, Producto
from apps.integraciones.clients import sipsa
from apps.integraciones.clients.sipsa import ClienteSipsa, SipsaNoDisponibleError
from apps.integraciones.models import PrecioReferencia

pytestmark = pytest.mark.integration


def _registro(ciudad, producto, precio, fecha):
    return (
        f"<return><ciudad>{ciudad}</ciudad><codProducto>1</codProducto><enviado>0</enviado>"
        f"<fechaCaptura>{fecha}T00:00:00-05:00</fechaCaptura>"
        f"<fechaCreacion>{fecha}T14:00:01-05:00</fechaCreacion>"
        f"<precioPromedio>{precio}</precioPromedio><producto>{producto}</producto>"
        f"<regId>1</regId></return>"
    )


RESPUESTA = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<S:Envelope xmlns:S="http://www.w3.org/2003/05/soap-envelope"><S:Body>'
    '<ns2:promediosSipsaCiudadResponse xmlns:ns2="http://servicios.sipsa.co.gov.dane/">'
    + _registro("ARMENIA", "Tomate*", "3455", "2026-11-12")
    + _registro("ARMENIA", "Tomate*", "3300", "2026-10-01")
    + _registro("ARMENIA", "Lulo", "5233", "2026-11-12")
    + _registro("PEREIRA", "Tomate*", "3000", "2026-11-12")
    + _registro("ARMENIA", "Coco", "no-es-precio", "2026-11-12")
    + "</ns2:promediosSipsaCiudadResponse></S:Body></S:Envelope>"
).encode()


class Transporte:
    def __init__(self, cuerpo=RESPUESTA, error=None):
        self.cuerpo, self.error, self.peticiones = cuerpo, error, []

    def __call__(self, url, cuerpo, cabeceras, timeout):
        self.peticiones.append((url, cuerpo, cabeceras, timeout))
        if self.error:
            raise self.error
        return BytesIO(self.cuerpo)


@pytest.fixture
def tomate(db):
    cat = Categoria.objects.create(nombre="Frutas y verduras", perecedera=True)
    p = Producto.objects.create(nombre="Tomate", nombre_normalizado="tomate", categoria=cat)
    Presentacion.objects.create(producto=p, cantidad=Decimal(1), unidad="kg")
    return p


def test_el_cliente_pide_la_operacion_por_soap_12_con_timeout():
    transporte = Transporte()
    cliente = ClienteSipsa(base_url="https://sipsa.test/ws", timeout_s=90, transporte=transporte)
    precios = cliente.promedios_ciudad(ciudad="ARMENIA", dias=7)
    url, cuerpo, cabeceras, timeout = transporte.peticiones[0]
    assert url == "https://sipsa.test/ws" and timeout == 90
    assert "application/soap+xml" in cabeceras["Content-Type"]
    assert b"promediosSipsaCiudad" in cuerpo
    assert {(p.producto, p.precio_por_kg, p.fecha) for p in precios} == {
        ("Tomate", Decimal("3455"), date(2026, 11, 12)),
        ("Lulo", Decimal("5233"), date(2026, 11, 12)),
    }
    assert {p.mercado for p in precios} == {"Armenia (SIPSA, promedio ciudad)"}


@pytest.mark.parametrize("error", [TimeoutError("lento"), OSError("sin red")])
def test_una_falla_de_red_se_traduce_a_no_disponible(error):
    cliente = ClienteSipsa(base_url="https://sipsa.test/ws", transporte=Transporte(error=error))
    with pytest.raises(SipsaNoDisponibleError):
        cliente.promedios_ciudad(ciudad="ARMENIA", dias=7)


def test_un_xml_roto_se_traduce_a_no_disponible():
    cliente = ClienteSipsa(base_url="https://sipsa.test/ws", transporte=Transporte(b"<S:Envelope>"))
    with pytest.raises(SipsaNoDisponibleError):
        cliente.promedios_ciudad(ciudad="ARMENIA", dias=7)


def test_el_xml_con_entidades_peligrosas_se_rechaza():
    bomba = b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa">]><x>&a;</x>'
    cliente = ClienteSipsa(base_url="https://sipsa.test/ws", transporte=Transporte(bomba))
    with pytest.raises(SipsaNoDisponibleError):
        cliente.promedios_ciudad(ciudad="ARMENIA", dias=7)


def _comando(monkeypatch, *args, transporte=None):
    transporte = transporte or Transporte()
    monkeypatch.setattr(sipsa, "_transporte_http", transporte)
    salida = StringIO()
    call_command("importar_sipsa", "--servicio-web", *args, stdout=salida)
    return salida.getvalue()


def test_el_comando_importa_lo_que_esta_en_el_catalogo_y_es_idempotente(monkeypatch, tomate):
    salida = _comando(monkeypatch)
    ref = PrecioReferencia.objects.get()
    assert (ref.producto, ref.precio_por_kg, ref.fecha) == (
        tomate,
        Decimal("3455"),
        date(2026, 11, 12),
    )
    assert "Lulo" in salida  # no está en el catálogo: se informa
    _comando(monkeypatch)
    assert PrecioReferencia.objects.count() == 1


def test_crear_faltantes_agrega_los_frescos_con_presentacion_de_un_kilo(monkeypatch, tomate):
    _comando(monkeypatch, "--crear-faltantes")
    lulo = Producto.objects.get(nombre="Lulo")
    assert lulo.marca is None and lulo.categoria.perecedera
    assert lulo.presentaciones.filter(cantidad=1, unidad="kg").exists()
    assert PrecioReferencia.objects.count() == 2


def test_sin_red_el_comando_falla_con_mensaje_claro(monkeypatch, db):
    with pytest.raises(CommandError, match="SIPSA"):
        _comando(monkeypatch, transporte=Transporte(error=OSError("sin red")))


def test_sin_archivo_ni_servicio_web_pide_uno(db):
    with pytest.raises(CommandError):
        call_command("importar_sipsa", stdout=StringIO())
