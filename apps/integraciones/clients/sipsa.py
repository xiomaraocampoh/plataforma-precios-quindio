"""Cliente de la fuente pública SIPSA (DANE) para la carga inicial de datos (pregunta de diseño 5).

Patrón puerto/adaptador: el resto del sistema depende de `FuentePreciosExterna`, no de SIPSA.
Así la fuente es reemplazable y se prueba con un doble (test double) sin red.
Resiliencia: timeout obligatorio; si falla, la plataforma sigue operando sin la fuente
(compatibilidad = prioridad baja). Circuit Breaker solo si la evidencia lo justifica (ADR).
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol

from django.conf import settings


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


class ClienteSipsa:
    def __init__(self, base_url: str | None = None, timeout_s: int | None = None) -> None:
        self.base_url = base_url or settings.INTEGRACIONES["SIPSA_BASE_URL"]
        self.timeout_s = timeout_s or settings.INTEGRACIONES["SIPSA_TIMEOUT_S"]

    def precios_del_dia(self, fecha: date) -> list[PrecioExterno]:
        # TODO(Corte II): implementar según el servicio publicado por el DANE y sus términos de uso.
        raise SipsaNoDisponibleError("Integración SIPSA pendiente de implementar.")
