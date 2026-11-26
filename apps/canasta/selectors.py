"""Lectura de la canasta: arma el resultado con los precios vigentes (ADR-0027).

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
    return _ALTERNAS[bases[0] if bases else Unidad.UNIDAD.value]


def elegir_producto(texto: str):
    """El producto del catálogo que corresponde a lo que escribió la persona.

    Entre los que coinciden con el nombre se elige el que más establecimientos con precio vigente
    tiene (más datos, sin criterio comercial); el empate se resuelve por nombre. Devuelve también
    hasta tres alternativas para poder avisar.
    """
    candidatos = list(catalogo.buscar_productos(texto, limite=10))
    if not candidatos and len(texto) > 3 and texto.endswith("s"):
        candidatos = list(catalogo.buscar_productos(texto[:-1], limite=10))  # «huevos» → «huevo»
    if not candidatos:
        return None, []
    filas = filas_vigentes_de([p.pk for p in candidatos])
    orden = sorted(candidatos, key=lambda p: (-len(filas.get(p.pk, [])), str(p).casefold()))
    return orden[0], orden[1:4]


def nombres_de(producto_ids: list[int]) -> dict[int, str]:
    return {p.pk: str(p) for p in catalogo.productos_publicos().filter(pk__in=producto_ids)}


@dataclass
class OpcionVista:
    opcion: object
    total_texto: str
    lugar: str
    mejor: bool
    lineas: list = field(default_factory=list)


@dataclass
class Resultado:
    opciones: list
    criterio: str
    texto_criterio: str
    sin_precios: bool


def _linea_vista(ln) -> dict:
    return {
        "linea": ln,
        "costo_texto": formatear_pesos(ln.costo),
        "presentacion_texto": f"{formatear_cantidad(ln.tamano)} {ln.unidad_presentacion}",
    }


def resultado(pedido: list[dict], criterio: str = CRITERIO_COBERTURA) -> Resultado:
    """Las tiendas ordenadas con el total, la cobertura y los faltantes de cada una."""
    if criterio not in CRITERIOS:
        criterio = CRITERIO_COBERTURA
    nombres = nombres_de([i["producto_id"] for i in pedido])
    items = [
        ItemCanasta(
            i["producto_id"], nombres[i["producto_id"]], Decimal(i["cantidad"]), i["unidad"]
        )
        for i in pedido
        if i["producto_id"] in nombres
    ]
    filas = filas_vigentes_de([i.producto_id for i in items]) if items else {}
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
    locales = {eid: nombre for eid, (nombre, _) in lugares.items()}
    ordenadas = ordenar_opciones(calcular_canasta(items, ofertas, locales), criterio)
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
    return Resultado(opciones, criterio, texto_criterio(criterio), bool(items) and not opciones)
