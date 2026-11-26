"""Canasta de compra: cuánto cuesta cada lista de productos en cada establecimiento.

Capa de dominio: Python puro, sin Django (ADR-0027 a 0029). Se desarrolla con TDD.

Reglas que no se negocian:
- Un producto sin precio vigente **no** se suma como cero: queda en `faltantes` y la cobertura lo
  dice («1 de 2»). Nada se inventa ni se estima con precios ajenos (ADR-0028, M-24).
- El costo de un producto es la cantidad pedida en unidad base por el precio por unidad de la
  presentación más conveniente del comercio (`precio_por_unidad`, nunca a mano; ADR-0029, M-05).
- El orden es solo el que se declara al usuario (`texto_criterio`); ninguna promoción, perfil
  verificado ni patrocinio entra en él (EC-06, M-06).
"""

import math
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from apps.catalogo.domain.normalizacion import (
    CENTAVOS,
    a_unidad_base,
    precio_por_unidad,
    son_comparables,
)

MAX_ITEMS = 20

CRITERIO_COBERTURA = "cobertura"
CRITERIO_TOTAL = "total"
_TEXTOS_CRITERIO = {
    CRITERIO_COBERTURA: "Ordenado por: más productos disponibles y luego menor total",
    CRITERIO_TOTAL: (
        "Ordenado por: menor total (los totales de tiendas incompletas no incluyen "
        "los productos que faltan)"
    ),
}


class CanastaInvalidaError(ValueError):
    """El pedido no se puede calcular (cantidad, unidad o tamaño de la lista)."""


@dataclass(frozen=True)
class ItemCanasta:
    producto_id: int
    nombre: str
    cantidad: Decimal
    unidad: str


@dataclass(frozen=True)
class OfertaPresentacion:
    """Un precio vigente de una presentación en un establecimiento (viene del selector)."""

    establecimiento_id: int
    producto_id: int
    presentacion_id: int
    tamano: Decimal
    unidad: str
    precio: Decimal


@dataclass(frozen=True)
class LineaCanasta:
    producto_id: int
    nombre: str
    presentacion_id: int
    tamano: Decimal
    unidad_presentacion: str
    cantidad_base: Decimal
    unidad_base: str
    precio_unitario: Decimal
    empaques: int
    costo: Decimal


@dataclass(frozen=True)
class OpcionCanasta:
    establecimiento_id: int
    establecimiento: str
    total: Decimal
    lineas: tuple[LineaCanasta, ...]
    faltantes: tuple[ItemCanasta, ...]

    @property
    def disponibles(self) -> int:
        return len(self.lineas)

    @property
    def pedidos(self) -> int:
        return len(self.lineas) + len(self.faltantes)

    @property
    def cobertura(self) -> str:
        return f"{self.disponibles} de {self.pedidos}"

    @property
    def completa(self) -> bool:
        return not self.faltantes


def validar_items(items: Iterable[ItemCanasta], unidades_por_producto: Mapping[int, set[str]]):
    """Rechaza lo que no se puede calcular.

    `unidades_por_producto`: las unidades de las presentaciones de cada producto.
    """
    lista = list(items)
    if not lista:
        raise CanastaInvalidaError("Agrega al menos un producto a la canasta.")
    if len(lista) > MAX_ITEMS:
        raise CanastaInvalidaError(f"Una canasta admite hasta {MAX_ITEMS} productos.")
    vistos: set[int] = set()
    for item in lista:
        if item.producto_id in vistos:
            raise CanastaInvalidaError(f"«{item.nombre}» está repetido en la canasta.")
        vistos.add(item.producto_id)
        if item.cantidad <= 0:
            raise CanastaInvalidaError(f"La cantidad de «{item.nombre}» debe ser mayor que cero.")
        conocidas = unidades_por_producto.get(item.producto_id, set())
        if conocidas and not any(son_comparables(item.unidad, u) for u in conocidas):
            raise CanastaInvalidaError(
                f"«{item.nombre}» no se mide en {item.unidad}; usa {', '.join(sorted(conocidas))}."
            )


def _mejor_oferta(item: ItemCanasta, ofertas: Iterable[OfertaPresentacion]):
    """La presentación de menor precio por unidad; empate: menor tamaño y luego menor id."""
    candidatas = []
    for o in ofertas:
        if o.producto_id != item.producto_id or not son_comparables(item.unidad, o.unidad):
            continue
        unitario, _ = precio_por_unidad(o.precio, o.tamano, o.unidad)
        tamano_base, _ = a_unidad_base(o.tamano, o.unidad)
        candidatas.append(((unitario, tamano_base, o.presentacion_id), o, unitario))
    if not candidatas:
        return None
    _, oferta, unitario = min(candidatas, key=lambda c: c[0])
    return oferta, unitario


def _linea(item: ItemCanasta, oferta: OfertaPresentacion, unitario: Decimal) -> LineaCanasta:
    cantidad_base, base = a_unidad_base(item.cantidad, item.unidad)
    tamano_base, _ = a_unidad_base(oferta.tamano, oferta.unidad)
    return LineaCanasta(
        producto_id=item.producto_id,
        nombre=item.nombre,
        presentacion_id=oferta.presentacion_id,
        tamano=oferta.tamano,
        unidad_presentacion=oferta.unidad,
        cantidad_base=cantidad_base,
        unidad_base=base.value,
        precio_unitario=unitario,
        empaques=math.ceil(cantidad_base / tamano_base),
        costo=(cantidad_base * unitario).quantize(CENTAVOS, rounding=ROUND_HALF_UP),
    )


def calcular_canasta(
    items: Iterable[ItemCanasta],
    ofertas: Iterable[OfertaPresentacion],
    establecimientos: Mapping[int, str],
) -> list[OpcionCanasta]:
    """Una opción por establecimiento que tenga al menos un precio vigente de la canasta.

    Sin orden garantizado: se ordena con `ordenar_opciones`.
    """
    pedido = list(items)
    por_local: dict[int, list[OfertaPresentacion]] = {}
    for o in ofertas:
        por_local.setdefault(o.establecimiento_id, []).append(o)
    opciones = []
    for local_id, ofertas_local in por_local.items():
        lineas, faltantes = [], []
        for item in pedido:
            elegida = _mejor_oferta(item, ofertas_local)
            if elegida is None:
                faltantes.append(item)
            else:
                lineas.append(_linea(item, *elegida))
        if not lineas:
            continue
        opciones.append(
            OpcionCanasta(
                establecimiento_id=local_id,
                establecimiento=establecimientos.get(local_id, ""),
                total=sum((ln.costo for ln in lineas), Decimal("0.00")),
                lineas=tuple(lineas),
                faltantes=tuple(faltantes),
            )
        )
    return opciones


def _sin_tildes(texto: str) -> str:
    base = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in base if not unicodedata.combining(c)).casefold()


def texto_criterio(criterio: str) -> str:
    try:
        return _TEXTOS_CRITERIO[criterio]
    except KeyError:
        raise ValueError(f"Criterio de orden desconocido: {criterio!r}.") from None


def ordenar_opciones(
    opciones: Iterable[OpcionCanasta], criterio: str = CRITERIO_COBERTURA
) -> list[OpcionCanasta]:
    """Orden declarado al usuario (ADR-0028). El id solo desempata para que sea determinista."""
    texto_criterio(criterio)  # valida el criterio

    def clave(o: OpcionCanasta):
        nombre = _sin_tildes(o.establecimiento)
        if criterio == CRITERIO_COBERTURA:
            return (-o.disponibles, o.total, nombre, o.establecimiento_id)
        return (o.total, -o.disponibles, nombre, o.establecimiento_id)

    return sorted(opciones, key=clave)
