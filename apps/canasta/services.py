"""El asistente de compras como conversación (sin IA por ahora; ADR-0030 pone la IA encima).

Entiende listas escritas a mano («2 kg arroz, 1 L leche») y órdenes cortas («menor total», «quita
la leche»). Toda cifra que dice sale del dominio de la canasta: nada se inventa. El estado vive en
la sesión (sin cuenta, sin tocar la base).
"""

import unicodedata
from dataclasses import dataclass
from decimal import Decimal

from apps.catalogo.domain.normalizacion import son_comparables

from . import selectors
from .domain.canasta import CRITERIO_COBERTURA, CRITERIO_TOTAL, MAX_ITEMS
from .domain.intencion import Tipo, detectar_intencion
from .domain.lista import parsear_lista

CLAVE_SESION = "asistente_v1"
MAX_MENSAJES = 30
MAX_ADJUNTO = 20_000  # caracteres de texto de un archivo adjunto
SALUDO_AYUDA = "Escribe o pega tu lista, por ejemplo: 2 kg arroz, 1 L leche, 12 huevos."


@dataclass(frozen=True)
class Adjunto:
    nombre: str
    texto: str = ""
    es_imagen: bool = False


def leer(sesion) -> dict:
    estado = sesion.get(CLAVE_SESION) or {}
    return {
        "mensajes": list(estado.get("mensajes", [])),
        "pedido": list(estado.get("pedido", [])),
        "criterio": estado.get("criterio", CRITERIO_COBERTURA),
    }


def _guardar(sesion, estado: dict) -> None:
    estado["mensajes"] = estado["mensajes"][-MAX_MENSAJES:]
    sesion[CLAVE_SESION] = estado
    sesion.modified = True


def _plano(texto: str) -> str:
    base = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in base if not unicodedata.combining(c))


def _interpretar(texto: str) -> tuple[list[dict], list[str], list[str]]:
    """(pedido, avisos, no_encontrados) de un texto con una lista."""
    pedido, avisos, no_encontrados, vistos, elegidos = [], [], [], set(), []
    for linea in parsear_lista(texto):
        producto, alternativas = selectors.elegir_producto(linea.producto)
        if producto is None:
            no_encontrados.append(linea.producto)
            continue
        if producto.pk in vistos:
            continue
        vistos.add(producto.pk)
        unidades = selectors.unidades_de(producto)
        unidad, cantidad = linea.unidad, linea.cantidad
        if unidad is not None and not any(son_comparables(unidad, u) for u in unidades):
            avisos.append(f"«{producto}» no se mide en {unidad}; usé {unidades[0]}.")
            unidad = cantidad = None
        pedido.append(
            {
                "producto_id": producto.pk,
                "cantidad": format((cantidad or Decimal(1)).normalize(), "f"),
                "unidad": unidad or unidades[0],
            }
        )
        if alternativas and producto.nombre_normalizado != _plano(linea.producto):
            elegidos.append(f"«{linea.producto}» → {producto}")
        if len(pedido) >= MAX_ITEMS:
            avisos.append(f"Tomé los primeros {MAX_ITEMS} productos.")
            break
    if elegidos:  # una sola línea, no una por producto
        avisos.append(
            "Elegí " + "; ".join(elegidos) + " (los que más precios tienen). "
            "Dime si prefieres otra marca."
        )
    return pedido, avisos, no_encontrados


def _texto_resultado(res, avisos: list[str], no_encontrados: list[str]) -> str:
    partes = []
    if res.sin_precios:
        partes.append(
            "Entendí tu lista, pero todavía nadie ha reportado precios vigentes de esos productos."
        )
    elif res.opciones:
        mejor = res.opciones[0]
        o = mejor.opcion
        if res.criterio == CRITERIO_TOTAL:
            partes.append(
                f"La opción de menor total es {o.establecimiento}: {mejor.total_texto} "
                f"(estimado), con {o.cobertura} productos."
            )
        elif o.completa:
            partes.append(
                f"Te conviene {o.establecimiento}: tiene todos tus productos y te sale en "
                f"{mejor.total_texto} (estimado)."
            )
        else:
            faltan = ", ".join(f.nombre for f in o.faltantes)
            partes.append(
                f"Ninguna tienda tiene todo. La que más productos tiene es "
                f"{o.establecimiento} ({o.cobertura}) por {mejor.total_texto}; le faltan: {faltan}."
            )
    partes.extend(avisos)
    if no_encontrados:
        partes.append("No encontré en el catálogo: " + ", ".join(no_encontrados) + ".")
    return " ".join(partes)


def _nueva_lista(estado: dict, entrada: str) -> tuple[str, bool]:
    pedido, avisos, faltan = _interpretar(entrada)
    if not pedido:
        if faltan:
            return "No encontré esos productos en el catálogo: " + ", ".join(faltan) + ".", False
        return f"No pude leer productos en tu mensaje. {SALUDO_AYUDA}", False
    estado["pedido"] = pedido
    res = selectors.resultado(pedido, estado["criterio"])
    return _texto_resultado(res, avisos, faltan), True


def _agregar(estado: dict, resto: str) -> tuple[str, bool]:
    nuevos, avisos, faltan = _interpretar(resto)
    ya = {i["producto_id"] for i in estado["pedido"]}
    estado["pedido"] = (estado["pedido"] + [i for i in nuevos if i["producto_id"] not in ya])[
        :MAX_ITEMS
    ]
    if not estado["pedido"]:
        return f"Aún no tienes lista. {SALUDO_AYUDA}", False
    res = selectors.resultado(estado["pedido"], estado["criterio"])
    return _texto_resultado(res, avisos, faltan), True


def _quitar(estado: dict, resto: str) -> tuple[str, bool]:
    nombres = selectors.nombres_de([i["producto_id"] for i in estado["pedido"]])
    palabras = [
        w for w in _plano(resto).split() if w not in {"el", "la", "los", "las", "de", "del"}
    ]
    fuera = {
        pid for pid, n in nombres.items() if palabras and all(w in _plano(n) for w in palabras)
    }
    if not fuera:
        return f"No encontré «{resto}» en tu lista.", bool(estado["pedido"])
    estado["pedido"] = [i for i in estado["pedido"] if i["producto_id"] not in fuera]
    quitados = ", ".join(nombres[p] for p in fuera)
    if not estado["pedido"]:
        return f"Quité {quitados}. Tu lista quedó vacía. {SALUDO_AYUDA}", False
    res = selectors.resultado(estado["pedido"], estado["criterio"])
    return f"Quité {quitados}. " + _texto_resultado(res, [], []), True


def _ordenar(estado: dict, criterio: str) -> tuple[str, bool]:
    if not estado["pedido"]:
        return f"Primero necesito tu lista. {SALUDO_AYUDA}", False
    estado["criterio"] = criterio
    res = selectors.resultado(estado["pedido"], criterio)
    return _texto_resultado(res, [], []), True


def responder(sesion, texto: str, adjunto: Adjunto | None = None) -> None:
    """Procesa un mensaje de la persona y deja en la sesión su respuesta."""
    estado = leer(sesion)
    texto = (texto or "").strip()
    visto = texto
    if adjunto:
        visto = (texto + "\n" if texto else "") + f"📎 {adjunto.nombre}"
    if not visto:
        return
    estado["mensajes"].append({"rol": "usuario", "texto": visto, "tarjeta": False})

    if adjunto and adjunto.es_imagen:
        respuesta, tarjeta = (
            (
                "Todavía no sé leer fotos de listas: eso lo hará la IA cuando esté activada. "
                f"Por ahora, {SALUDO_AYUDA[0].lower() + SALUDO_AYUDA[1:]}"
            ),
            False,
        )
    else:
        entrada = (texto + "\n" + adjunto.texto[:MAX_ADJUNTO]).strip() if adjunto else texto
        intencion = detectar_intencion(entrada)
        if intencion.tipo is Tipo.REINICIAR:
            estado["pedido"] = []
            respuesta, tarjeta = f"Listo, empecemos de nuevo. {SALUDO_AYUDA}", False
        elif intencion.tipo is Tipo.ORDENAR_TOTAL:
            respuesta, tarjeta = _ordenar(estado, CRITERIO_TOTAL)
        elif intencion.tipo is Tipo.ORDENAR_COBERTURA:
            respuesta, tarjeta = _ordenar(estado, CRITERIO_COBERTURA)
        elif intencion.tipo is Tipo.AGREGAR:
            respuesta, tarjeta = _agregar(estado, intencion.resto)
        elif intencion.tipo is Tipo.QUITAR:
            respuesta, tarjeta = _quitar(estado, intencion.resto)
        else:
            respuesta, tarjeta = _nueva_lista(estado, intencion.resto)
    estado["mensajes"].append({"rol": "asistente", "texto": respuesta, "tarjeta": tarjeta})
    _guardar(sesion, estado)


def reiniciar(sesion) -> None:
    sesion[CLAVE_SESION] = {}
    sesion.modified = True
