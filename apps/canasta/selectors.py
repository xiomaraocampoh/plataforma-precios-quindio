"""Lectura de la canasta: arma el panel con los precios vigentes (ADR-0027).

Los precios salen de `comparacion.selectors.filas_vigentes_de` (la misma caché por producto que la
comparación). El cálculo y el orden son del dominio; aquí solo se prepara lo que se muestra.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from apps.catalogo import selectors as catalogo
from apps.catalogo.domain.normalizacion import Unidad, a_unidad_base, formatear_cantidad
from apps.comparacion.domain.tarjeta import formatear_pesos
from apps.comparacion.selectors import filas_vigentes_de

from .domain.canasta import (
    CRITERIO_COBERTURA,
    CRITERIO_TOTAL,
    ItemCanasta,
    OfertaPresentacion,
    calcular_canasta,
    ordenar_opciones,
    texto_criterio,
)

CRITERIOS = (CRITERIO_COBERTURA, CRITERIO_TOTAL)
_ALTERNAS = {"kg": ("kg", "g"), "L": ("L", "ml"), "und": ("und",)}


def unidades_de(producto) -> tuple[str, ...]:
    """Unidades en que se puede pedir un producto, la más natural primero (kg, g / L, ml / und)."""
    bases = []
    for p in producto.presentaciones.all():
        if p.activa:
            base = a_unidad_base(Decimal(1), p.unidad)[1].value
            if base not in bases:
                bases.append(base)
    base = bases[0] if bases else Unidad.UNIDAD.value
    return _ALTERNAS[base]


@dataclass
class FilaPedido:
    producto: object
    cantidad: str
    unidad: str
    unidades: tuple[str, ...]


@dataclass
class OpcionVista:
    opcion: object
    total_texto: str
    lugar: str
    mejor: bool
    lineas: list = field(default_factory=list)


@dataclass
class Panel:
    pedido: list
    opciones: list
    criterio: str
    texto_criterio: str
    sin_precios: bool


def productos_buscables(texto: str):
    return catalogo.buscar_productos(texto, limite=8)


def producto_de(producto_id: int):
    return catalogo.con_fotos(catalogo.productos_publicos()).filter(pk=producto_id).first()


def _linea_vista(ln) -> dict:
    return {
        "linea": ln,
        "costo_texto": formatear_pesos(ln.costo),
        "presentacion_texto": f"{formatear_cantidad(ln.tamano)} {ln.unidad_presentacion}",
    }


def panel(items_sesion: list[dict], criterio: str = CRITERIO_COBERTURA) -> Panel:
    if criterio not in CRITERIOS:
        criterio = CRITERIO_COBERTURA
    ids = [i["producto_id"] for i in items_sesion]
    productos = {
        p.pk: p
        for p in catalogo.con_fotos(catalogo.productos_publicos())
        .filter(pk__in=ids)
        .prefetch_related("presentaciones")
    }
    pedido = [
        FilaPedido(
            productos[i["producto_id"]],
            i["cantidad"],
            i["unidad"],
            unidades_de(productos[i["producto_id"]]),
        )
        for i in items_sesion
        if i["producto_id"] in productos
    ]
    items = [
        ItemCanasta(f.producto.pk, str(f.producto), Decimal(f.cantidad), f.unidad) for f in pedido
    ]
    filas = filas_vigentes_de([f.producto.pk for f in pedido]) if pedido else {}
    ofertas, lugares = [], {}
    for pid, lista in filas.items():
        for fila in lista:
            r = fila.resultado
            ofertas.append(
                OfertaPresentacion(
                    r.establecimiento_id,
                    pid,
                    fila.presentacion_id,
                    fila.cantidad,
                    fila.unidad,
                    r.precio,
                )
            )
            lugares[r.establecimiento_id] = (r.establecimiento, fila)
    nombres = {eid: nombre for eid, (nombre, _) in lugares.items()}
    ordenadas = ordenar_opciones(calcular_canasta(items, ofertas, nombres), criterio)
    opciones = []
    for n, o in enumerate(ordenadas):
        fila = lugares[o.establecimiento_id][1]
        sitio = ", ".join(x for x in (fila.barrio, fila.municipio) if x)
        opciones.append(
            OpcionVista(
                opcion=o,
                total_texto=formatear_pesos(o.total),
                lugar=f"{fila.tipo} · {sitio}" if sitio else fila.tipo,
                mejor=n == 0,
                lineas=[_linea_vista(ln) for ln in o.lineas],
            )
        )
    return Panel(
        pedido, opciones, criterio, texto_criterio(criterio), bool(pedido) and not opciones
    )
