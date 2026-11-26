"""K-nasta con IA: el bucle de herramientas (ADR-0030).

La IA interpreta y explica; el sistema calcula. Ella solo puede llamar tres herramientas de solo
lectura (buscar productos, armar la lista, calcular tiendas) y todo lo que escribe se contrasta con
lo que devolvieron: si menciona una cifra que no salió del cálculo, se descarta (EC-14). Si algo
falla, quien llama sigue con las reglas.
"""

import json
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.urls import reverse

from apps.integraciones import services as integraciones
from apps.integraciones.domain.asistente import (
    HERRAMIENTAS,
    INSTRUCCIONES,
    MAX_BUSQUEDAS,
    MAX_HISTORIAL,
    MAX_LLAMADAS,
    MAX_TEXTO_MODELO,
    MAX_VUELTAS,
    cifras_permitidas,
    texto_sin_cifras_inventadas,
)

from . import selectors
from .domain.canasta import MAX_ITEMS, CanastaInvalidaError, ItemCanasta, validar_items
from .domain.guia import TEMAS, buscar_temas

_ROL = {"usuario": "user", "asistente": "assistant"}


@dataclass(frozen=True)
class Turno:
    texto: str | None  # None: el texto de la IA no es confiable y el sistema redacta el suyo
    tarjeta: bool


def _buscar(args: dict, estado: dict) -> dict:
    textos = [str(t).strip()[:80] for t in (args.get("textos") or []) if str(t).strip()]
    if not textos:
        return {"ok": False, "error": "Indica al menos un nombre de producto."}
    return {
        "ok": True,
        "resultados": [
            {"texto": t, "productos": selectors.candidatos(t)} for t in textos[:MAX_BUSQUEDAS]
        ],
    }


def _armar(args: dict, estado: dict) -> dict:
    crudos = args.get("items") or []
    if not crudos or len(crudos) > MAX_ITEMS:
        return {"ok": False, "error": f"La lista debe tener entre 1 y {MAX_ITEMS} productos."}
    productos = selectors.productos_por_ids([i.get("producto_id") for i in crudos])
    items, pedido = [], []
    for i in crudos:
        producto = productos.get(i.get("producto_id"))
        if producto is None:
            return {"ok": False, "error": f"No existe el producto_id {i.get('producto_id')}."}
        try:
            cantidad = Decimal(str(i.get("cantidad")))
        except InvalidOperation:
            return {"ok": False, "error": f"Cantidad inválida para {producto}."}
        items.append(ItemCanasta(producto.pk, str(producto), cantidad, str(i.get("unidad"))))
        pedido.append({"producto_id": producto.pk, "cantidad": cantidad, "unidad": i["unidad"]})
    try:
        validar_items(items, {p.pk: set(selectors.unidades_de(p)) for p in productos.values()})
    except CanastaInvalidaError as exc:
        return {"ok": False, "error": str(exc)}
    estado["pedido"] = [{**p, "cantidad": format(p["cantidad"].normalize(), "f")} for p in pedido]
    return {
        "ok": True,
        "calculo": _calcular({"criterio": estado["criterio"]}, estado),  # una vuelta menos
        "items": [
            {
                "producto_id": p["producto_id"],
                "nombre": str(productos[p["producto_id"]]),
                "cantidad": p["cantidad"],
                "unidad": p["unidad"],
            }  # fmt: skip
            for p in estado["pedido"]
        ],
    }


def _calcular(args: dict, estado: dict) -> dict:
    if not estado["pedido"]:
        return {"ok": False, "error": "Primero arma la canasta con armar_canasta."}
    criterio = args.get("criterio") if args.get("criterio") in selectors.CRITERIOS else "cobertura"
    res = selectors.resultado(estado["pedido"], criterio)
    estado["criterio"] = criterio
    return {
        "ok": True,
        "criterio": res.texto_criterio,
        "tiendas_con_algun_precio": len(res.opciones),
        "opciones": [
            {
                "establecimiento": o.opcion.establecimiento,
                "lugar": o.lugar,
                "total": int(o.opcion.total.quantize(Decimal(1), rounding=ROUND_HALF_UP)),
                "total_texto": o.total_texto,
                "cobertura": o.opcion.cobertura,
                "completa": o.opcion.completa,
                "faltantes": [f.nombre for f in o.opcion.faltantes],
            }
            for o in res.opciones[:5]
        ],
    }


def _guia(args: dict, estado: dict) -> dict:
    temas = buscar_temas(str(args.get("consulta", ""))[:200], limite=2)
    if not temas:
        return {
            "ok": False,
            "error": "La guía no cubre eso.",
            "temas_disponibles": [t.titulo for t in TEMAS],
        }
    # Los botones y el paso a paso los pone el sistema (no la IA): solo rutas y temas reales
    estado["_extras"] = {
        "acciones": [{"texto": texto, "url": reverse(ruta)} for texto, ruta in temas[0].acciones],
        "tema": temas[0].id,
    }
    return {
        "ok": True,
        "temas": [
            {"titulo": t.titulo, "pasos": t.textos, "botones": [a[0] for a in t.acciones]}
            for t in temas
        ],
    }


_DE_CANASTA = {"armar_canasta", "calcular_canasta"}
_EJECUTORES = {
    "buscar_productos": _buscar,
    "armar_canasta": _armar,
    "calcular_canasta": _calcular,
    "consultar_guia": _guia,
}


def _ejecutar(llamada: dict, estado: dict) -> str:
    funcion = _EJECUTORES.get(llamada.get("name"))
    if funcion is None:
        resultado = {"ok": False, "error": "Herramienta desconocida."}
    else:
        resultado = funcion(llamada.get("input") or {}, estado)
    return json.dumps(resultado, ensure_ascii=False)


def _historial(mensajes: list[dict]) -> list[dict]:
    """Los últimos mensajes como texto (sin tarjetas), empezando por uno de la persona."""
    recientes = [{"role": _ROL[m["rol"]], "content": m["texto"]} for m in mensajes[-MAX_HISTORIAL:]]
    while recientes and recientes[0]["role"] != "user":
        recientes.pop(0)
    return recientes


def _contexto_de_la_lista(estado: dict) -> str:
    if not estado["pedido"]:
        return ""
    nombres = selectors.nombres_de([i["producto_id"] for i in estado["pedido"]])
    lineas = [
        f"- {nombres.get(i['producto_id'], '?')} (producto_id {i['producto_id']}): "
        f"{i['cantidad']} {i['unidad']}"
        for i in estado["pedido"]
    ]
    return "\n\nLISTA ACTUAL DE LA PERSONA (datos):\n" + "\n".join(lineas)


def conversar(
    estado: dict, historial: list[dict], entrada: str, imagen, *, usuario, ip: str
) -> Turno:
    """Un mensaje de la persona. Puede cambiar `estado["pedido"]` y `estado["criterio"]`.

    Lanza `LimiteDelAsistenteExcedidoError` o `AsistenteNoDisponibleError`: quien llama sigue
    con las reglas.
    """
    integraciones.exigir_cupo_del_asistente(usuario, ip)
    modelo = integraciones.crear_asistente()
    contenido = [{"type": "text", "text": entrada or "Esta es mi lista del mercado."}]
    if imagen is not None:
        contenido.insert(0, integraciones.bloque_imagen(*imagen))
    mensajes = [*_historial(historial), {"role": "user", "content": contenido}]
    temas = "; ".join(t.titulo for t in TEMAS)
    sistema = (
        INSTRUCCIONES
        + f"\n\nTEMAS DE LA GUÍA DE USO (datos): {temas}"
        + _contexto_de_la_lista(estado)
    )

    devueltos: list[str] = []
    vueltas = llamadas = 0
    uso_canasta = False
    respuesta = None
    while True:
        respuesta = modelo.responder(sistema=sistema, mensajes=mensajes, herramientas=HERRAMIENTAS)
        pedidas = respuesta.llamadas
        if respuesta.parada != "tool_use" or not pedidas:
            break
        vueltas += 1
        llamadas += len(pedidas)
        if vueltas > MAX_VUELTAS or llamadas > MAX_LLAMADAS:
            respuesta = None  # demasiadas vueltas: el sistema redacta con lo calculado
            break
        resultados = []
        for llamada in pedidas:
            uso_canasta = uso_canasta or llamada.get("name") in _DE_CANASTA
            salida = _ejecutar(llamada, estado)
            devueltos.append(salida)
            resultados.append(
                {"type": "tool_result", "tool_use_id": llamada["id"], "content": salida}
            )
        mensajes += [
            {"role": "assistant", "content": respuesta.bloques},
            {"role": "user", "content": resultados},
        ]

    hay_lista = (
        bool(estado["pedido"]) and uso_canasta
    )  # una pregunta de ayuda no muestra la tarjeta
    texto = respuesta.texto if respuesta is not None and respuesta.parada == "end_turn" else ""
    permitidas = cifras_permitidas(entrada or "", *devueltos, json.dumps(estado["pedido"]))
    confiable = bool(texto) and len(texto) <= MAX_TEXTO_MODELO
    if confiable and not texto_sin_cifras_inventadas(texto, permitidas):
        confiable = False  # EC-14: una cifra que no salió del cálculo
    return Turno(texto if confiable else None, hay_lista)
