"""Cliente de la fuente pública SIPSA (DANE) para la carga inicial de datos (pregunta de diseño 5).

Patrón puerto/adaptador: el resto del sistema depende de `FuentePreciosExterna`, no de SIPSA.
Así la fuente es reemplazable y se prueba con un doble (test double) sin red.
Resiliencia: timeout obligatorio; si falla, la plataforma sigue operando sin la fuente
(compatibilidad = prioridad baja). Circuit Breaker solo si la evidencia lo justifica (ADR).
"""

import csv
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from io import StringIO
from typing import Protocol
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

import defusedxml.ElementTree as DefusedET
from defusedxml import DefusedXmlException
from django.conf import settings

from apps.catalogo.domain.duplicados import normalizar_nombre
from apps.integraciones.domain.sipsa import (
    RegistroCiudad,
    interpretar_fecha,
    interpretar_precio_cop,
    recientes_de_la_ciudad,
    registro_desde_campos,
)


@dataclass(frozen=True)
class PrecioExterno:
    producto: str
    mercado: str
    precio_por_kg: Decimal
    fecha: date


class FuentePreciosExterna(Protocol):
    def precios_del_dia(self, fecha: date) -> list[PrecioExterno]: ...


class SipsaNoDisponibleError(RuntimeError):
    pass


class ArchivoSipsaInvalidoError(ValueError):
    """El CSV no tiene las columnas producto, mercado, precio y fecha."""


@dataclass
class LecturaSipsa:
    precios: list[PrecioExterno] = field(default_factory=list)
    errores: list[tuple[int, str]] = field(default_factory=list)


_COLUMNAS = {  # encabezado normalizado → campo
    "producto": "producto",
    "mercado": "mercado",
    "precio": "precio",
    "precio promedio": "precio",
    "precio por kg": "precio",
    "precio_por_kg": "precio",
    "precio promedio por kilogramo": "precio",
    "fecha": "fecha",
}


def leer_csv_sipsa(lineas: Iterable[str]) -> LecturaSipsa:
    """Adaptador de archivo (RF-07): CSV descargado a mano del DANE → PrecioExterno.

    Acepta «;» o «,», encabezados con tildes o mayúsculas y precios en formato colombiano.
    Una fila inválida se informa (línea y motivo) y no detiene la importación.
    """
    texto = "".join(lineas)
    dialecto = csv.Sniffer().sniff(texto.splitlines()[0] if texto else ",", delimiters=";,")
    lector = csv.DictReader(StringIO(texto), dialect=dialecto)
    campos = {
        _COLUMNAS[normalizar_nombre(c).replace("_", " ")]: c
        for c in lector.fieldnames or []
        if normalizar_nombre(c).replace("_", " ") in _COLUMNAS
    }
    faltan = {"producto", "mercado", "precio", "fecha"} - campos.keys()
    if faltan:
        raise ArchivoSipsaInvalidoError(f"Faltan columnas: {', '.join(sorted(faltan))}.")
    lectura = LecturaSipsa()
    for linea, fila in enumerate(lector, start=2):
        try:
            lectura.precios.append(
                PrecioExterno(
                    producto=fila[campos["producto"]].strip(),
                    mercado=fila[campos["mercado"]].strip(),
                    precio_por_kg=interpretar_precio_cop(fila[campos["precio"]] or ""),
                    fecha=interpretar_fecha(fila[campos["fecha"]] or ""),
                )
            )
        except ValueError as exc:
            lectura.errores.append((linea, str(exc)))
    return lectura


URL_SIPSA_DANE = "https://appweb.dane.gov.co/sipsaWS/SrvSipsaUpraBeanService"
_SOBRE = (
    '<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" '
    'xmlns:ns="http://servicios.sipsa.co.gov.dane/"><soap:Header/>'
    "<soap:Body><ns:{operacion}/></soap:Body></soap:Envelope>"
)
_CAMPOS_CIUDAD = frozenset({"ciudad", "producto", "precioPromedio", "fechaCaptura"})


def _transporte_http(url: str, cuerpo: bytes, cabeceras: dict, timeout: int):
    """POST real al DANE. Devuelve la respuesta como archivo (se lee en streaming)."""
    if not url.startswith("https://"):
        raise SipsaNoDisponibleError("SIPSA_BASE_URL debe usar https.")
    peticion = Request(url, data=cuerpo, headers=cabeceras, method="POST")  # noqa: S310
    return urlopen(peticion, timeout=timeout)  # noqa: S310 — esquema validado arriba


def _local(etiqueta: str) -> str:
    return etiqueta.rsplit("}", 1)[-1]


def leer_respuesta_ciudad(flujo, ciudad: str) -> list[RegistroCiudad]:
    """Recorre el XML (~120 MB, todas las ciudades) sin cargarlo entero y guarda solo `ciudad`.

    defusedxml rechaza DTD y entidades (bombas XML): la respuesta es de un tercero.
    """
    registros, campos = [], {}
    for _, elemento in DefusedET.iterparse(flujo, events=("end",)):
        nombre = _local(elemento.tag)
        if nombre in _CAMPOS_CIUDAD:
            campos[nombre] = elemento.text or ""
        elif nombre == "return":
            if " ".join(campos.get("ciudad", "").lower().split()) == ciudad.lower():
                try:
                    registros.append(registro_desde_campos(campos))
                except ValueError:
                    pass  # un registro mal formado del DANE no detiene la importación
            campos = {}
            elemento.clear()
    return registros


class ClienteSipsa:
    """Adaptador del servicio web SOAP 1.2 de SIPSA (DANE). Sin autenticación; datos públicos.

    El DANE publica los precios diarios después de las 2 p. m. La respuesta de
    `promediosSipsaCiudad` trae todas las ciudades y el historial: tarda ~1 min. Por eso se usa
    desde un comando (`importar_sipsa --servicio-web`), nunca dentro de una petición web.
    """

    def __init__(
        self, base_url: str | None = None, timeout_s: int | None = None, transporte=None
    ) -> None:
        integraciones = settings.INTEGRACIONES
        self.base_url = base_url or integraciones["SIPSA_BASE_URL"] or URL_SIPSA_DANE
        self.timeout_s = timeout_s or integraciones.get("SIPSA_SOAP_TIMEOUT_S", 180)
        self._transporte = transporte

    def _llamar(self, operacion: str):
        transporte = self._transporte or _transporte_http
        cabeceras = {
            "Content-Type": f'application/soap+xml; charset=utf-8; action="{operacion}"',
            "User-Agent": "plataforma-precios-quindio/1.0 (RF-07)",
        }
        cuerpo = _SOBRE.format(operacion=operacion).encode()
        try:
            return transporte(self.base_url, cuerpo, cabeceras, self.timeout_s)
        except (OSError, TimeoutError) as exc:  # URLError es OSError
            raise SipsaNoDisponibleError(f"SIPSA no respondió: {type(exc).__name__}.") from exc

    def promedios_ciudad(self, *, ciudad: str = "ARMENIA", dias: int = 7) -> list[PrecioExterno]:
        """Precio promedio por kg de cada producto en `ciudad`, de los últimos `dias` días."""
        flujo = self._llamar("promediosSipsaCiudad")
        try:
            registros = leer_respuesta_ciudad(flujo, ciudad)
        except (ET.ParseError, DefusedXmlException, OSError) as exc:
            raise SipsaNoDisponibleError(
                f"Respuesta de SIPSA ilegible: {type(exc).__name__}."
            ) from exc
        finally:
            getattr(flujo, "close", lambda: None)()
        mercado = f"{ciudad.strip().title()} (SIPSA, promedio ciudad)"
        return [
            PrecioExterno(r.producto, mercado, r.precio, r.fecha)
            for r in recientes_de_la_ciudad(registros, ciudad=ciudad, dias=dias)
        ]

    def precios_del_dia(self, fecha: date) -> list[PrecioExterno]:
        """Puerto FuentePreciosExterna: lo publicado ese día en Armenia."""
        return [p for p in self.promedios_ciudad(dias=1) if p.fecha == fecha]
