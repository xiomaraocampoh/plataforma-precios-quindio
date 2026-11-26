"""Puerto de extensiones de la comparación (ADR-012, DP-1 opción B). Python puro — TDD.

La comparación declara aquí QUÉ datos comerciales acepta (precio oficial y promociones por
establecimiento y presentación) y el protocolo que debe cumplir quien los aporte. No sabe quién es:
el módulo comercial se registra en `core.extensiones` con el nombre `PUNTO_DATOS_COMERCIALES` y la
comparación nunca lo importa.

Nada de esto entra en `ranking._clave_neutral` (EC-06): el precio oficial reemplaza al reportado
como el precio del establecimiento (ADR-018) y las promociones son solo etiqueta (ADR-014).
"""

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol, runtime_checkable

from .tarjeta import formatear_pesos, texto_por_unidad

PUNTO_DATOS_COMERCIALES = "comparacion.datos_comerciales"

Par = tuple[int, int]  # (establecimiento_id, presentacion_id)


@dataclass(frozen=True)
class PrecioOficialVigente:
    """Precio publicado por un comercio VERIFICADO (ADR-015). La vigencia de 30 días la decide la
    comparación con `precios.domain.vigencia` (fuente «comercio»)."""

    producto_id: int
    establecimiento_id: int
    presentacion_id: int
    precio: Decimal
    confirmado_en: datetime


@dataclass(frozen=True)
class PromocionComparacion:
    """Una promoción vigente lista para mostrar: textos y cifras ya calculados por quien la aporta.

    `precio_efectivo` es por empaque; en «pague X lleve Y», el promedio por empaque llevando Y.
    """

    producto_id: int
    establecimiento_id: int
    presentacion_id: int
    tipo: str
    descripcion: str
    precio_efectivo: Decimal
    precio_efectivo_unitario: Decimal
    unidad_base: str
    inicio: datetime
    fin: datetime
    motivo: str
    condiciones: str
    fecha_vencimiento_producto: date | None = None

    @property
    def precio_texto(self) -> str:
        return formatear_pesos(self.precio_efectivo)

    @property
    def por_unidad_texto(self) -> str:
        return texto_por_unidad(self.precio_efectivo_unitario, self.unidad_base)


@dataclass(frozen=True)
class DatosComerciales:
    oficiales: tuple[PrecioOficialVigente, ...] = ()
    promociones: tuple[PromocionComparacion, ...] = ()

    def oficiales_por_par(self) -> dict[Par, PrecioOficialVigente]:
        return {(o.establecimiento_id, o.presentacion_id): o for o in self.oficiales}

    def promociones_por_par(self) -> dict[Par, list[PromocionComparacion]]:
        grupos: dict[Par, list[PromocionComparacion]] = defaultdict(list)
        for p in self.promociones:
            grupos[(p.establecimiento_id, p.presentacion_id)].append(p)
        return dict(grupos)


@runtime_checkable
class ExtensionComparacion(Protocol):
    """Lo que debe cumplir un módulo que aporta datos comerciales a la comparación."""

    def datos_para(self, producto_ids: Sequence[int], ahora: datetime) -> DatosComerciales: ...


def reunir_datos(
    extensiones: Iterable[ExtensionComparacion], producto_ids: Sequence[int], ahora: datetime
) -> DatosComerciales:
    """Suma lo que aporta cada extensión, en orden de registro. Sin extensiones: nada."""
    ids = list(producto_ids)
    if not ids:
        return DatosComerciales()
    oficiales: list[PrecioOficialVigente] = []
    promociones: list[PromocionComparacion] = []
    for extension in extensiones:
        datos = extension.datos_para(ids, ahora)
        oficiales.extend(datos.oficiales)
        promociones.extend(datos.promociones)
    return DatosComerciales(oficiales=tuple(oficiales), promociones=tuple(promociones))
