"""El asistente de compras como conversación (sin IA por ahora; ADR-0030 pone la IA encima).

Entiende listas escritas a mano («2 kg arroz, 1 L leche») y órdenes cortas («menor total», «quita
la leche»). Toda cifra que dice sale del dominio de la canasta: nada se inventa. El estado vive en
la sesión (sin cuenta, sin tocar la base).
"""

import unicodedata
from dataclasses import dataclass
from decimal import Decimal

from django.urls import reverse

from apps.catalogo.domain.normalizacion import son_comparables
from apps.integraciones import services as integraciones
from apps.integraciones.domain.reconocimiento import ImagenInvalidaError, tipo_de_imagen

from . import ia, selectors
from .domain.canasta import CRITERIO_COBERTURA, CRITERIO_TOTAL, MAX_ITEMS
from .domain.guia import Tema, buscar_temas, tema_por_id
from .domain.intencion import Intencion, Tipo, detectar_intencion
from .domain.lista import parsear_lista

CLAVE_SESION = "asistente_v1"
MAX_MENSAJES = 30
MAX_ADJUNTO = 20_000  # caracteres de texto de un archivo adjunto
SALUDO_AYUDA = "Escribe o pega tu lista, por ejemplo: 2 kg arroz, 1 L leche, 12 huevos."
SIN_FOTOS = (
    "Todavía no sé leer fotos de listas: eso lo hace la IA cuando está activada. "
    "Por ahora, escribe o pega tu lista, por ejemplo: 2 kg arroz, 1 L leche, 12 huevos."
)
COMANDOS_LOCALES = {Tipo.REINICIAR, Tipo.ORDENAR_TOTAL, Tipo.ORDENAR_COBERTURA}


@dataclass(frozen=True)
class Adjunto:
    nombre: str
    texto: str = ""
    es_imagen: bool = False
    imagen: bytes = b""  # solo se usa con la IA; nunca se guarda


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


PRINCIPALES = ("registrar", "comparar", "cuenta", "canasta")  # lo que se sugiere al empezar


def _acciones_de(tema: Tema) -> list[dict]:
    return [{"texto": texto, "url": reverse(ruta)} for texto, ruta in tema.acciones]


def _texto_de_tema(tema: Tema) -> str:
    pasos = "\n".join(f"{n}. {paso}" for n, paso in enumerate(tema.pasos, 1))
    return f"**{tema.titulo}**\n{pasos}"


def _sugerir(estado: dict, temas, **extras) -> None:
    estado["_extras"] = {
        **extras,
        "sugerencias": [{"texto": t.titulo, "tema": t.id} for t in temas],
    }


def _responder_tema(estado: dict, tema: Tema, relacionados=()) -> tuple[str, bool]:
    _sugerir(estado, relacionados, acciones=_acciones_de(tema))
    return _texto_de_tema(tema), False


def _ayuda(estado: dict, entrada: str) -> tuple[str, bool]:
    """Una pregunta sobre cómo usar la app: se responde con la guía (nunca se inventa)."""
    temas = buscar_temas(entrada, limite=2)
    if temas:
        return _responder_tema(estado, temas[0], temas[1:])
    _sugerir(estado, [tema_por_id(i) for i in PRINCIPALES])
    return (
        "Con gusto te ayudo a usar AhorraPues. Elige un tema o cuéntame qué quieres hacer, "
        "o pásame tu lista del mercado.",
        False,
    )


def _con_reglas(estado: dict, intencion) -> tuple[str, bool]:
    if intencion.tipo is Tipo.AYUDA:
        return _ayuda(estado, intencion.resto)
    if intencion.tipo is Tipo.REINICIAR:
        estado["pedido"] = []
        return f"Listo, empecemos de nuevo. {SALUDO_AYUDA}", False
    if intencion.tipo is Tipo.ORDENAR_TOTAL:
        return _ordenar(estado, CRITERIO_TOTAL)
    if intencion.tipo is Tipo.ORDENAR_COBERTURA:
        return _ordenar(estado, CRITERIO_COBERTURA)
    if intencion.tipo is Tipo.AGREGAR:
        return _agregar(estado, intencion.resto)
    if intencion.tipo is Tipo.QUITAR:
        return _quitar(estado, intencion.resto)
    return _nueva_lista(estado, intencion.resto)


def _con_ia(estado, historial, entrada, adjunto, usuario, ip) -> tuple[str, bool]:
    """K-nasta con IA (ADR-0030). Si el texto de la IA no es confiable, redacta el sistema."""
    imagen = None
    if adjunto is not None and adjunto.es_imagen:
        try:
            imagen = (adjunto.imagen, tipo_de_imagen(adjunto.imagen))
        except ImagenInvalidaError as exc:
            return str(exc), False
    turno = ia.conversar(estado, historial, entrada, imagen, usuario=usuario, ip=ip)
    if turno.texto is not None:
        return turno.texto, turno.tarjeta
    if turno.tarjeta:
        res = selectors.resultado(estado["pedido"], estado["criterio"])
        return _texto_resultado(res, [], []), True
    return "No logré darte una respuesta confiable. ¿Me cuentas de nuevo qué vas a comprar?", False


def _respuesta(estado, historial, entrada, adjunto, usuario, ip) -> tuple[str, bool]:
    es_imagen = adjunto is not None and adjunto.es_imagen
    usa_ia = integraciones.asistente_ia_activo()
    if es_imagen and not usa_ia:
        return SIN_FOTOS, False
    intencion = Intencion(Tipo.LISTA, entrada) if es_imagen else detectar_intencion(entrada)
    if intencion.tipo in COMANDOS_LOCALES or not usa_ia:  # órdenes cortas: gratis, sin IA
        return _con_reglas(estado, intencion)
    try:
        return _con_ia(estado, historial, entrada, adjunto, usuario, ip)
    except integraciones.LimiteDelAsistenteExcedidoError:
        aviso = (
            "Llegué a mi límite de consultas con IA por ahora, así que respondo en modo básico. "
        )
    except integraciones.AsistenteNoDisponibleError:
        aviso = "No pude usar la IA en este momento, así que respondo en modo básico. "
    if es_imagen:
        return aviso + SIN_FOTOS, False
    texto, tarjeta = _con_reglas(estado, intencion)
    return aviso + texto, tarjeta


def _registrar(sesion, estado, visto: str, respuesta: str, tarjeta: bool) -> None:
    extras = estado.pop("_extras", {})
    mensaje = {"rol": "asistente", "texto": respuesta, "tarjeta": tarjeta}
    mensaje.update({k: v for k, v in extras.items() if v})
    estado["mensajes"].append(mensaje)
    _guardar(sesion, estado)


def responder(sesion, texto: str, adjunto: Adjunto | None = None, *, usuario=None, ip="") -> None:
    """Procesa un mensaje de la persona y deja en la sesión su respuesta."""
    estado = leer(sesion)
    texto = (texto or "").strip()
    visto = texto
    if adjunto:
        visto = (texto + "\n" if texto else "") + f"📎 {adjunto.nombre}"
    if not visto:
        return
    historial = list(estado["mensajes"])
    estado["mensajes"].append({"rol": "usuario", "texto": visto, "tarjeta": False})
    if adjunto and adjunto.es_imagen:
        entrada = texto
    else:
        entrada = (texto + "\n" + adjunto.texto[:MAX_ADJUNTO]).strip() if adjunto else texto
    respuesta, tarjeta = _respuesta(estado, historial, entrada, adjunto, usuario, ip)
    _registrar(sesion, estado, visto, respuesta, tarjeta)


def responder_tema(sesion, texto: str, tema_id: str) -> bool:
    """Un botón de la guía: responde ese tema, sin IA y sin costo. False si no existe."""
    tema = tema_por_id(tema_id)
    if tema is None:
        return False
    estado = leer(sesion)
    estado["mensajes"].append(
        {"rol": "usuario", "texto": (texto or tema.titulo)[:200], "tarjeta": False}
    )
    relacionados = [t for t in buscar_temas(tema.titulo, limite=3) if t.id != tema.id][:1]
    respuesta, tarjeta = _responder_tema(estado, tema, relacionados)
    _registrar(sesion, estado, "", respuesta, tarjeta)
    return True


def reiniciar(sesion) -> None:
    sesion[CLAVE_SESION] = {}
    sesion.modified = True
