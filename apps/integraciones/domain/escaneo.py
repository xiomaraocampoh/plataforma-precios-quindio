"""Escaneo en vivo (RF-04 y RF-11 ampliados, ADR-0026). Python puro — TDD.

Dos reglas:
- `interpretar_escaneo`: qué reconoció la IA en un fotograma (un empaque, una etiqueta de precio o
  nada), validado por los mismos filtros que la foto manual.
- `decidir_envio` / `debe_enviar_fotograma`: cuándo vale la pena gastar una consulta. El navegador
  (static/js/escanear.js) aplica esta misma regla con los parámetros que el servidor le entrega.
"""

import math
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from .etiqueta import PRECIO_MAXIMO_ETIQUETA, EtiquetaPrecio, interpretar_etiqueta
from .reconocimiento import PistaProducto, interpretar_respuesta


class TipoEscaneo(StrEnum):
    PRODUCTO = "producto"
    ETIQUETA = "etiqueta"
    NADA = "nada"


@dataclass(frozen=True)
class ResultadoEscaneo:
    tipo: TipoEscaneo
    pista: PistaProducto | None = None  # con qué buscar el producto en el catálogo
    etiqueta: EtiquetaPrecio | None = None  # solo si es una etiqueta de precio válida

    @classmethod
    def nada(cls) -> "ResultadoEscaneo":
        return cls(TipoEscaneo.NADA)


def interpretar_escaneo(
    crudo, *, precio_maximo: Decimal = PRECIO_MAXIMO_ETIQUETA
) -> ResultadoEscaneo:
    """Una etiqueta exige que la IA la clasifique así y un precio válido; si no, se intenta como
    producto; si tampoco hay nombre ni código, no hay nada que mostrar."""
    if not isinstance(crudo, dict) or crudo.get("tipo") == TipoEscaneo.NADA:
        return ResultadoEscaneo.nada()
    pista = interpretar_respuesta(crudo)
    if crudo.get("tipo") == TipoEscaneo.ETIQUETA:
        etiqueta = interpretar_etiqueta(crudo, precio_maximo=precio_maximo)
        if etiqueta is not None:
            return ResultadoEscaneo(TipoEscaneo.ETIQUETA, pista=pista, etiqueta=etiqueta)
    if pista is None:
        return ResultadoEscaneo.nada()
    return ResultadoEscaneo(TipoEscaneo.PRODUCTO, pista=pista)


class Espera(StrEnum):
    """Por qué no se envía el fotograma (o LISTO si sí)."""

    LISTO = "listo"
    PAUSADO = "pausado"
    TOPE = "tope"
    EN_CURSO = "en_curso"
    MUY_PRONTO = "muy_pronto"
    MOVIDA = "movida"
    BORROSA = "borrosa"


@dataclass(frozen=True)
class ControlDeEnvio:
    intervalo_ms: int = 1500  # mínimo entre dos envíos
    max_por_sesion: int = 20  # al llegar, se pausa y se ofrece «Seguir escaneando»
    umbral_movimiento: float = 0.05  # diferencia media entre cuadros reducidos (0 a 1)
    umbral_nitidez: float = 40.0  # varianza del laplaciano en gris (0 a 255)

    def __post_init__(self):
        if self.intervalo_ms < 0:
            raise ValueError("El intervalo no puede ser negativo.")
        if self.max_por_sesion < 1:
            raise ValueError("La sesión debe permitir al menos un fotograma.")
        if not 0 < self.umbral_movimiento <= 1:
            raise ValueError("El umbral de movimiento va entre 0 (excluido) y 1.")
        if self.umbral_nitidez < 0:
            raise ValueError("El umbral de nitidez no puede ser negativo.")


def decidir_envio(
    *,
    control: ControlDeEnvio,
    diferencia: float,
    nitidez: float,
    ms_desde_ultimo: int | None,
    en_curso: bool,
    enviados: int,
    pausado: bool,
) -> Espera:
    """Primero lo que la persona controla (pausa, tope), luego el ritmo y al final la imagen."""
    if enviados < 0 or (ms_desde_ultimo is not None and ms_desde_ultimo < 0):
        raise ValueError("Los contadores no pueden ser negativos.")
    if pausado:
        return Espera.PAUSADO
    if enviados >= control.max_por_sesion:
        return Espera.TOPE
    if en_curso:
        return Espera.EN_CURSO
    if ms_desde_ultimo is not None and ms_desde_ultimo < control.intervalo_ms:
        return Espera.MUY_PRONTO
    if math.isnan(diferencia) or diferencia >= control.umbral_movimiento:
        return Espera.MOVIDA
    if math.isnan(nitidez) or nitidez < control.umbral_nitidez:
        return Espera.BORROSA
    return Espera.LISTO


def debe_enviar_fotograma(**kwargs) -> bool:
    return decidir_envio(**kwargs) is Espera.LISTO
