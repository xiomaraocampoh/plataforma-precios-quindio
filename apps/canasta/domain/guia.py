"""Guía de uso de AhorraPues: lo que K-nasta explica a quien llega por primera vez. Python puro.

Es la ÚNICA fuente de lo que K-nasta dice sobre cómo usar la app (con o sin IA): cada paso describe
algo que existe de verdad (botones y textos reales). Si cambia una pantalla, se cambia aquí.
Los destinos son nombres de ruta («app:nombre»); la capa de servicios los convierte en enlaces.
"""

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class Tema:
    id: str
    titulo: str
    pasos: tuple[str, ...]
    acciones: tuple[tuple[str, str], ...]  # (texto del botón, «app:nombre» de la ruta)
    patrones: tuple[tuple[str, int], ...]  # (expresión sobre texto sin tildes, peso)

    @property
    def corto(self) -> str:
        """Etiqueta breve para un botón (la conversación muestra el título completo)."""
        return _VISTA[self.id][0]

    @property
    def icono(self) -> str:
        return _VISTA[self.id][1]


# id → (etiqueta corta del botón, ícono del sprite)
_VISTA = {
    "que_es": ("¿Qué es AhorraPues?", "i-info"),
    "comparar": ("Comparar precios", "i-scale"),
    "cuenta": ("Crear una cuenta", "i-user"),
    "registrar": ("Registrar un precio", "i-plus"),
    "confirmar": ("Confirmar o denunciar", "i-check"),
    "escanear": ("Usar la cámara", "i-camara"),
    "vigencia": ("Precios vigentes", "i-clock"),
    "producto_faltante": ("Un producto no está", "i-search"),
    "tienda_faltante": ("Una tienda no está", "i-store"),
    "mis_aportes": ("Mis aportes", "i-chart"),
    "apariencia": ("Modo claro u oscuro", "i-info"),
    "comercio": ("Tengo un comercio", "i-store"),
    "privacidad": ("Mis datos", "i-shield"),
    "contrasena": ("Olvidé mi contraseña", "i-user"),
    "canasta": ("Armar mi mercado", "i-box"),
}


def _t(id, titulo, pasos, acciones, patrones) -> Tema:
    return Tema(id, titulo, tuple(pasos), tuple(acciones), tuple(patrones))


TEMAS: tuple[Tema, ...] = (
    _t(
        "que_es",
        "¿Qué es AhorraPues?",
        [
            "AhorraPues compara los precios de la canasta familiar entre tiendas de barrio, "
            "minimercados y supermercados de Armenia y el Quindío.",
            "Los precios los reporta la comunidad; no vendemos nada ni somos un sistema oficial.",
            "Para consultar y comparar no necesitas cuenta. La cuenta sirve para registrar o "
            "confirmar precios.",
        ],
        [("Ir al inicio", "comparacion:inicio")],
        [
            (r"\bque es (ahorrapues|esto|esta pagina|la pagina|la app|la plataforma)\b", 5),
            (r"\bpara que sirve\b", 5),
            (r"\bque (hace|haces|puedes hacer|puedo hacer)\b", 4),
            (r"\bprimeros pasos\b|\bprimera vez\b|\btutorial\b|\bempezar\b", 3),
        ],
    ),
    _t(
        "comparar",
        "¿Cómo comparo precios de un producto?",
        [
            "Escribe el producto en el buscador de la portada (por ejemplo «arroz») o entra a "
            "«Productos».",
            "Toca el producto: verás cada tienda con su precio, el precio por kilo o litro (para "
            "comparar empaques de distinto tamaño) y hace cuánto se reportó.",
            "La primera tienda es la de menor precio por unidad. El orden es el mismo para todos: "
            "ninguna tienda paga por salir primero.",
            "Si quieres, filtra por municipio, barrio o rango de precio.",
        ],
        [("Ver productos", "comparacion:productos")],
        [
            (r"\bcompar\w*", 3),
            (r"\bmas barat\w*", 3),
            (r"\bdonde\b.{0,40}\bbarat\w*", 3),
            (r"\b(tienda|supermercado|minimercado)\b.{0,30}\b(barat\w*|conviene)", 3),
            (r"\b(buscar|busco|ver|veo|consultar|consulto)\b.{0,15}\bprecios?\b", 2),
        ],
    ),
    _t(
        "cuenta",
        "¿Cómo creo una cuenta?",
        [
            "Toca «Crear cuenta» (arriba a la derecha).",
            "Elige un nombre de usuario (de 3 a 30 caracteres) y una contraseña de 8 caracteres o "
            "más, que no sea solo números.",
            "El correo es opcional: solo sirve para recuperar tu contraseña y no se publica.",
            "Marca la autorización de datos y pulsa «Crear cuenta». Tu nombre nunca se muestra "
            "junto a los precios.",
        ],
        [("Crear cuenta", "cuentas:registro"), ("Ingresar", "cuentas:ingresar")],
        [
            (r"\b(crear|creo|abrir|abro|hacer|hago|sacar|saco)\b.{0,12}\bcuenta\b", 4),
            (r"\bregistrarme\b|\bregistrarse\b|\binscrib\w*|\bunirme\b|\bunirse\b", 4),
            (r"\bregistr(ar|o)\b(?!.{0,10}\bprecio)", 2),
            (r"\b(cuenta|usuario|ingresar|iniciar sesion)\b", 1),
        ],
    ),
    _t(
        "registrar",
        "¿Cómo registro un precio?",
        [
            "Necesitas una cuenta: ingresa o crea una.",
            "Toca «Registrar precio». Paso 1: busca el producto o toca uno de la lista.",
            "Paso 2: elige la presentación exacta (por ejemplo 500 g o 1 kg), la tienda donde "
            "estás y escribe el precio total del empaque, tal como lo marca la etiqueta. Pulsa "
            "«Guardar precio».",
            "Atajo: en la comparación de un producto, el botón «Registrar precio aquí» ya trae el "
            "producto y la tienda elegidos.",
            "Tu reporte es anónimo: guardamos tu autoría solo para evitar abusos.",
        ],
        [("Registrar un precio", "precios:registrar"), ("Crear cuenta", "cuentas:registro")],
        [
            (r"\b(registr|report|sub|anot|agreg|pong|carg)\w*\b.{0,25}\bprecios?\b", 4),
            (r"\bprecios?\b.{0,25}\b(registr|report|sub|anot)\w*", 3),
            (r"\breport(ar|o|e)\b", 2),
        ],
    ),
    _t(
        "confirmar",
        "¿Cómo confirmo o denuncio un precio?",
        [
            "Entra a la comparación de un producto con tu cuenta.",
            "Si el precio de una tienda sigue igual, toca «Sigue igual»: lo hace más confiable y "
            "lo mantiene vigente.",
            "Si es incorrecto o abusivo, abre «Denunciar», cuenta el motivo y envíalo; moderación "
            "lo revisa.",
            "No puedes confirmar ni denunciar los precios que reportaste tú.",
        ],
        [("Ver productos", "comparacion:productos")],
        [
            (r"\b(confirm\w*|sigue igual|denunci\w*|reclam\w*)\b", 4),
            (r"\bprecio\b.{0,20}\b(mal|equivocad\w*|incorrect\w*|falso|raro)\b", 3),
        ],
    ),
    _t(
        "escanear",
        "¿Cómo busco con la cámara o el código de barras?",
        [
            "En el buscador de la portada toca el ícono de la cámara y permite el acceso.",
            "Apunta al código de barras del empaque: tu teléfono lo lee solo y te lleva a la "
            "comparación. También puedes escribir el número que está bajo las barras.",
            "Si está disponible, también puedes tomar una foto del producto o elegir una de tu "
            "galería para que lo reconozca.",
        ],
        [("Ir al inicio", "comparacion:inicio")],
        [(r"\b(escane\w*|camara|codigo de barras|barras|foto)\b", 4)],
    ),
    _t(
        "vigencia",
        "¿Por qué un precio ya no aparece o qué significa «confianza»?",
        [
            "Un precio se muestra como vigente por 7 días (3 días en productos que se dañan "
            "rápido, como frutas o carnes). Después deja de mostrarse hasta que alguien lo "
            "confirme o registre uno nuevo.",
            "«Confianza media» quiere decir que lo reportó una persona; «alta», que varias "
            "personas lo confirmaron o lo publicó el comercio; «baja», que se aleja de los demás "
            "precios y conviene verificarlo.",
            "Ayudas a mantenerlos al día con «Sigue igual» o registrando el precio de hoy.",
        ],
        [("Registrar un precio", "precios:registrar")],
        [
            (r"\b(vigent\w*|vencid\w*|venc\w*|caduc\w*|desactualizad\w*)\b", 4),
            (r"\bconfianza\b", 4),
            (r"\bya no (aparece|sale|se ve)\b|\bpor que no hay precio", 4),
        ],
    ),
    _t(
        "producto_faltante",
        "¿Qué hago si no encuentro un producto?",
        [
            "Búscalo por nombre o por código de barras; a veces está con otra marca o tamaño.",
            "Si no está, con tu cuenta toca «Solicitar el producto» y escribe su nombre, marca y "
            "presentación.",
            "Moderación lo revisa y, cuando lo aprueba, ya puedes registrarle precios.",
        ],
        [
            ("Solicitar un producto", "catalogo:solicitar"),
            ("Ver productos", "comparacion:productos"),
        ],
        [
            (r"\b(no encuentro|no aparece|no esta|falta|no existe)\b.{0,20}\bproducto", 4),
            (
                r"\b(agreguen|agregar|anadan|anadir|solicitar|solicito|pedir|pido)\b.{0,25}\bproducto",
                4,
            ),
            (r"\bproducto\b.{0,20}\b(nuevo|no esta|no existe|no aparece)", 3),
        ],
    ),
    _t(
        "tienda_faltante",
        "¿Y si mi tienda no está en el directorio?",
        [
            "Entra a «Establecimientos» (el directorio de tiendas).",
            "Con tu cuenta, toca «Sugerir establecimiento» y llena el nombre, el tipo y la "
            "dirección.",
            "Moderación lo revisa y, al aprobarlo, ya se pueden registrar precios en esa tienda.",
        ],
        [
            ("Sugerir establecimiento", "establecimientos:sugerir"),
            ("Ver el directorio", "establecimientos:directorio"),
        ],
        [
            (
                r"\b(tienda|establecimiento|local|negocio|supermercado|minimercado)\b.{0,25}"
                r"\b(no esta|no aparece|falta|nuevo|sugerir|agregar|agrego)",
                4,
            ),
            (r"\b(sugerir|sugiero|sugerencia)\b.{0,25}\b(tienda|establecimiento|local)", 4),
            (r"\bdirectorio\b", 3),
        ],
    ),
    _t(
        "mis_aportes",
        "¿Dónde veo mis aportes?",
        [
            "Ingresa a tu cuenta y abre el menú con tu nombre de usuario (arriba a la derecha).",
            "Elige «Mis aportes»: ahí están los precios que has registrado y su estado.",
        ],
        [("Mis aportes", "precios:mis_aportes")],
        [(r"\bmis (aportes|reportes|precios)\b|\blo que (he|ya) (reportado|registrado)", 5)],
    ),
    _t(
        "apariencia",
        "¿Cómo cambio entre modo claro y oscuro?",
        [
            "Toca el ícono de sol o luna, arriba a la derecha.",
            "Abajo en cada página, en «Apariencia», eliges Automática (sigue a tu dispositivo), "
            "Clara u Oscura. La app recuerda tu elección.",
        ],
        [],
        [(r"\b(modo oscuro|modo claro|oscuro|apariencia|tema)\b", 5)],
    ),
    _t(
        "comercio",
        "Tengo un comercio: ¿cómo publico mis precios?",
        [
            "Ingresa con tu cuenta y abre el menú con tu nombre de usuario.",
            "Elige «¿Tienes un comercio?» y crea el perfil de tu negocio.",
            "Un moderador verifica el perfil. Cuando está verificado puedes publicar tus precios "
            "oficiales (se muestran como «Oficial») y tus promociones.",
            "Las promociones se señalan, pero no cambian la posición de tu tienda en la "
            "comparación.",
        ],
        [("Mi comercio", "comercios:inicio")],
        [
            (r"\b(tengo|soy|mi|dueno de) (un |una )?(comercio|negocio|tienda)\b", 3),
            (r"\bcomercio\b", 3),
            (r"\bpublic\w*\b.{0,20}\bprecios?\b", 3),
        ],
    ),
    _t(
        "privacidad",
        "¿Mis datos son públicos?",
        [
            "No. Tu reporte es anónimo: nunca se muestra tu nombre, tu usuario, tu correo ni tu "
            "ubicación junto a un precio.",
            "Guardamos tu autoría solo para evitar abusos y moderar.",
            "En «Mis datos» puedes ver qué guardamos y pedir que lo suprimamos. La política de "
            "datos explica todo, incluido el uso de IA.",
        ],
        [("Política de datos", "cuentas:politica_datos"), ("Mis datos", "cuentas:mis_datos")],
        [
            (r"\b(mis datos|borrar mis datos|eliminar mi cuenta|suprimir)\b", 4),
            (r"\b(datos|privacidad|anonim\w*|publicos?)\b", 3),
        ],
    ),
    _t(
        "contrasena",
        "Olvidé mi contraseña",
        [
            "En «Ingresar», toca «¿Olvidaste tu contraseña?».",
            "Escribe tu nombre de usuario o tu correo y te enviaremos un enlace para crear una "
            "nueva (solo si registraste un correo).",
        ],
        [("Recuperar contraseña", "cuentas:recuperar")],
        [(r"\b(contrasena|clave|password)\b", 4), (r"\bolvide\b", 2)],
    ),
    _t(
        "canasta",
        "¿Cómo armo mi mercado completo?",
        [
            "Escríbeme tu lista aquí mismo, por ejemplo: «2 kg arroz, 1 L leche, 12 huevos». "
            "También puedes pegarla o adjuntar un archivo.",
            "Te digo en qué tienda te sale más barato comprarlo todo y qué productos le faltan a "
            "las demás.",
            "Puedes pedirme «menor total», «agrega leche» o «quita el arroz».",
        ],
        [],
        [(r"\b(mercado|canasta)\b", 3), (r"\barmar\b.{0,10}\blista", 4), (r"\bk ?nasta\b", 3)],
    ),
)

_POR_ID = {t.id: t for t in TEMAS}


def _plano(texto: str) -> str:
    base = unicodedata.normalize("NFKD", (texto or "").lower())
    sin_tildes = "".join(c for c in base if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", sin_tildes)).strip()


def tema_por_id(id: str) -> Tema | None:
    return _POR_ID.get(id)


def buscar_temas(texto: str, limite: int = 2) -> list[Tema]:
    """Los temas de la guía que más se parecen a la pregunta, el más afín primero."""
    plano = _plano(texto)
    if not plano:
        return []
    puntajes = []
    for orden, tema in enumerate(TEMAS):
        puntos = sum(peso for patron, peso in tema.patrones if re.search(patron, plano))
        if puntos:
            puntajes.append((-puntos, orden, tema))
    return [t for _, _, t in sorted(puntajes)[:limite]]
