"""Escaneo en vivo (ADR-0026): qué devolvió la IA y cuándo enviar un fotograma. Dominio puro."""

from decimal import Decimal

import pytest

from apps.integraciones.domain.escaneo import (
    ControlDeEnvio,
    Espera,
    ResultadoEscaneo,
    TipoEscaneo,
    debe_enviar_fotograma,
    decidir_envio,
    interpretar_escaneo,
)
from apps.integraciones.domain.etiqueta import EtiquetaPrecio
from apps.integraciones.domain.reconocimiento import PistaProducto

pytestmark = pytest.mark.unit


def _crudo(**cambios):
    base = {
        "tipo": "producto",
        "nombre": "Café molido",
        "marca": "Sello Rojo",
        "cantidad": "250",
        "unidad": "g",
        "codigo_barras": "",
        "confianza": "alta",
        "precio": "",
        "precio_anterior": "",
        "es_promocion": False,
        "precio_por_unidad": "",
        "unidad_precio_por_unidad": "",
        "referencia": "",
        "establecimiento": "",
    }
    return {**base, **cambios}


# --- interpretar_escaneo ------------------------------------------------------------------------
def test_un_empaque_es_un_producto():
    r = interpretar_escaneo(_crudo())
    assert r.tipo is TipoEscaneo.PRODUCTO
    assert r.pista == PistaProducto("Café molido", "Sello Rojo", "250", "g", "", "alta")
    assert r.etiqueta is None


def test_una_etiqueta_de_precio():
    r = interpretar_escaneo(_crudo(tipo="etiqueta", precio="$8.950"))
    assert r.tipo is TipoEscaneo.ETIQUETA
    assert isinstance(r.etiqueta, EtiquetaPrecio)
    assert r.etiqueta.precio == Decimal("8950")
    assert r.pista is not None and r.pista.nombre == "Café molido"  # para buscar en el catálogo


def test_una_etiqueta_sin_precio_legible_cae_a_producto():
    r = interpretar_escaneo(_crudo(tipo="etiqueta", precio="ilegible"))
    assert r.tipo is TipoEscaneo.PRODUCTO and r.etiqueta is None


def test_una_etiqueta_con_precio_absurdo_cae_a_producto():
    r = interpretar_escaneo(_crudo(tipo="etiqueta", precio="$9.000"), precio_maximo=Decimal("5000"))
    assert r.tipo is TipoEscaneo.PRODUCTO


def test_nada_reconocible():
    assert interpretar_escaneo(_crudo(tipo="nada")).tipo is TipoEscaneo.NADA
    assert interpretar_escaneo(_crudo(nombre="", codigo_barras="")).tipo is TipoEscaneo.NADA


@pytest.mark.parametrize("crudo", [None, "producto", [], 7])
def test_una_respuesta_rara_es_nada(crudo):
    assert interpretar_escaneo(crudo) == ResultadoEscaneo.nada()


def test_un_tipo_desconocido_se_interpreta_por_los_datos():
    assert interpretar_escaneo(_crudo(tipo="ordena-borrar")).tipo is TipoEscaneo.PRODUCTO


def test_un_producto_con_precio_no_se_vuelve_etiqueta_sin_que_la_ia_lo_diga():
    # solo es etiqueta si la IA la clasificó así: un precio suelto en un empaque no basta
    assert interpretar_escaneo(_crudo(precio="$1.000")).tipo is TipoEscaneo.PRODUCTO


def test_tipo_nada_gana_aunque_venga_texto():
    assert interpretar_escaneo(_crudo(tipo="nada", nombre="Arroz")).tipo is TipoEscaneo.NADA


# --- debe_enviar_fotograma ----------------------------------------------------------------------
CONTROL = ControlDeEnvio(
    intervalo_ms=1500, max_por_sesion=20, umbral_movimiento=0.05, umbral_nitidez=40.0
)


def _decidir(**cambios):
    base = {
        "diferencia": 0.01,
        "nitidez": 120.0,
        "ms_desde_ultimo": None,
        "en_curso": False,
        "enviados": 0,
        "pausado": False,
    }
    return decidir_envio(control=CONTROL, **{**base, **cambios})


def test_imagen_quieta_y_nitida_se_envia():
    assert _decidir() is Espera.LISTO
    assert debe_enviar_fotograma(
        control=CONTROL,
        diferencia=0.01,
        nitidez=120.0,
        ms_desde_ultimo=None,
        en_curso=False,
        enviados=0,
        pausado=False,
    )


def test_pausado_no_envia():
    assert _decidir(pausado=True) is Espera.PAUSADO


def test_tope_de_la_sesion():
    assert _decidir(enviados=19) is Espera.LISTO
    assert _decidir(enviados=20) is Espera.TOPE
    assert _decidir(enviados=21) is Espera.TOPE


def test_un_envio_a_la_vez():
    assert _decidir(en_curso=True) is Espera.EN_CURSO


def test_intervalo_minimo_entre_envios():
    assert _decidir(ms_desde_ultimo=1499) is Espera.MUY_PRONTO
    assert _decidir(ms_desde_ultimo=1500) is Espera.LISTO
    assert _decidir(ms_desde_ultimo=0) is Espera.MUY_PRONTO


def test_imagen_en_movimiento():
    assert _decidir(diferencia=0.0499) is Espera.LISTO
    assert _decidir(diferencia=0.05) is Espera.MOVIDA  # «por debajo» del umbral: estricto
    assert _decidir(diferencia=0.8) is Espera.MOVIDA


def test_imagen_borrosa():
    assert _decidir(nitidez=39.9) is Espera.BORROSA
    assert _decidir(nitidez=40.0) is Espera.LISTO
    assert _decidir(nitidez=0.0) is Espera.BORROSA


def test_medidas_no_numericas_no_envian():
    assert _decidir(diferencia=float("nan")) is Espera.MOVIDA
    assert _decidir(nitidez=float("nan")) is Espera.BORROSA


def test_el_orden_de_los_motivos_prioriza_lo_que_la_persona_puede_resolver():
    # pausado > tope > en curso > muy pronto > movida > borrosa
    assert _decidir(pausado=True, enviados=99, en_curso=True) is Espera.PAUSADO
    assert _decidir(enviados=99, en_curso=True) is Espera.TOPE
    assert _decidir(en_curso=True, ms_desde_ultimo=10) is Espera.EN_CURSO
    assert _decidir(ms_desde_ultimo=10, diferencia=0.9) is Espera.MUY_PRONTO
    assert _decidir(diferencia=0.9, nitidez=0.0) is Espera.MOVIDA


@pytest.mark.parametrize(
    "malos",
    [{"enviados": -1}, {"ms_desde_ultimo": -5}],
)
def test_contadores_negativos_son_un_error(malos):
    with pytest.raises(ValueError):
        _decidir(**malos)


@pytest.mark.parametrize(
    "campos",
    [
        {"intervalo_ms": -1},
        {"max_por_sesion": 0},
        {"umbral_movimiento": 0},
        {"umbral_movimiento": 1.5},
        {"umbral_nitidez": -1},
    ],
)
def test_el_control_valida_sus_parametros(campos):
    base = {
        "intervalo_ms": 1500,
        "max_por_sesion": 20,
        "umbral_movimiento": 0.05,
        "umbral_nitidez": 40.0,
    }
    with pytest.raises(ValueError):
        ControlDeEnvio(**{**base, **campos})
