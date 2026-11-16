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

from django.conf import settings

from apps.catalogo.domain.duplicados import normalizar_nombre
from apps.integraciones.domain.sipsa import interpretar_fecha, interpretar_precio_cop


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


class ClienteSipsa:
    def __init__(self, base_url: str | None = None, timeout_s: int | None = None) -> None:
        self.base_url = base_url or settings.INTEGRACIONES["SIPSA_BASE_URL"]
        self.timeout_s = timeout_s or settings.INTEGRACIONES["SIPSA_TIMEOUT_S"]

    def precios_del_dia(self, fecha: date) -> list[PrecioExterno]:
        # PENDIENTE (documentado en docs/integraciones/sipsa.md): el DANE no publica una API
        # estable con términos de uso para consumo automático. Mientras tanto, RF-07 se cubre con
        # el CSV descargado a mano: `python manage.py importar_sipsa archivo.csv`.
        raise SipsaNoDisponibleError("Cliente SIPSA en línea pendiente; use importar_sipsa.")
