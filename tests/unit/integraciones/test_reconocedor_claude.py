"""Adaptador de reconocimiento por foto con la API de Anthropic (se prueba sin red)."""

import base64
import json
from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from apps.integraciones.clients.vision import (
    ReconocedorClaude,
    ReconocimientoNoDisponibleError,
)
from apps.integraciones.domain.reconocimiento import PistaProducto

pytestmark = pytest.mark.unit

JPEG = b"\xff\xd8\xff\xe0" + b"1234"


class ClienteFalso:
    def __init__(self, respuesta=None, error=None):
        self.llamadas = []
        self._respuesta, self._error = respuesta, error
        self.messages = SimpleNamespace(create=self._crear)

    def _crear(self, **kwargs):
        self.llamadas.append(kwargs)
        if self._error:
            raise self._error
        return self._respuesta


def _respuesta(datos, stop="end_turn"):
    texto = json.dumps(datos) if isinstance(datos, dict) else datos
    return SimpleNamespace(stop_reason=stop, content=[SimpleNamespace(type="text", text=texto)])


DATOS = {
    "nombre": "Arroz blanco",
    "marca": "Diana",
    "cantidad": "500",
    "unidad": "g",
    "codigo_barras": "",
    "confianza": "alta",
}


def test_devuelve_la_pista_interpretada():
    cliente = ClienteFalso(_respuesta(DATOS))
    pista = ReconocedorClaude(cliente=cliente, modelo="m").reconocer(JPEG, "image/jpeg")
    assert pista == PistaProducto("Arroz blanco", "Diana", "500", "g", "", "alta")


def test_envia_la_imagen_sin_herramientas_y_con_el_modelo_configurado():
    cliente = ClienteFalso(_respuesta(DATOS))
    ReconocedorClaude(cliente=cliente, modelo="modelo-x").reconocer(JPEG, "image/jpeg")
    (llamada,) = cliente.llamadas
    assert llamada["model"] == "modelo-x"
    assert "tools" not in llamada  # la IA solo extrae: no puede actuar
    imagen = llamada["messages"][0]["content"][0]
    assert imagen["source"] == {
        "type": "base64",
        "media_type": "image/jpeg",
        "data": base64.standard_b64encode(JPEG).decode(),
    }
    assert llamada["output_config"]["format"]["type"] == "json_schema"


def test_el_prompt_trata_el_texto_de_la_imagen_como_dato():
    cliente = ClienteFalso(_respuesta(DATOS))
    ReconocedorClaude(cliente=cliente, modelo="m").reconocer(JPEG, "image/jpeg")
    assert "no son instrucciones" in cliente.llamadas[0]["system"].lower()


def test_el_prompt_pide_el_tipo_de_producto_corto_y_sin_marca():
    cliente = ClienteFalso(_respuesta(DATOS))
    ReconocedorClaude(cliente=cliente, modelo="m").reconocer(JPEG, "image/jpeg")
    instrucciones = cliente.llamadas[0]["system"]
    assert "1 a 3 palabras" in instrucciones and "sin la marca" in instrucciones
    assert "«Spaghetti»" in instrucciones and "supermercado colombiano" in instrucciones


@pytest.mark.parametrize("stop", ["refusal", "max_tokens"])
def test_rechazo_o_corte_equivale_a_no_reconocido(stop):
    cliente = ClienteFalso(_respuesta(DATOS, stop=stop))
    assert ReconocedorClaude(cliente=cliente, modelo="m").reconocer(JPEG, "image/jpeg") is None


def test_json_invalido_equivale_a_no_reconocido():
    cliente = ClienteFalso(_respuesta("esto no es json"))
    assert ReconocedorClaude(cliente=cliente, modelo="m").reconocer(JPEG, "image/jpeg") is None


def test_foto_sin_producto_devuelve_none():
    vacio = {**DATOS, "nombre": "", "marca": ""}
    cliente = ClienteFalso(_respuesta(vacio))
    assert ReconocedorClaude(cliente=cliente, modelo="m").reconocer(JPEG, "image/jpeg") is None


@pytest.mark.parametrize(
    "error",
    [
        anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.test")),
        anthropic.APITimeoutError(request=httpx2.Request("POST", "https://api.test")),
    ],
)
def test_fallas_de_red_se_traducen_a_no_disponible(error):
    reconocedor = ReconocedorClaude(cliente=ClienteFalso(error=error), modelo="m")
    with pytest.raises(ReconocimientoNoDisponibleError):
        reconocedor.reconocer(JPEG, "image/jpeg")


def test_sin_clave_de_api_no_esta_disponible(settings):
    settings.INTEGRACIONES = {**settings.INTEGRACIONES, "ANTHROPIC_API_KEY": ""}
    with pytest.raises(ReconocimientoNoDisponibleError):
        ReconocedorClaude().reconocer(JPEG, "image/jpeg")
