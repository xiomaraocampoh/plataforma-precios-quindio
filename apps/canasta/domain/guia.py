"""Guía de uso de AhorraPues: lo que K-nasta explica a quien llega por primera vez. Python puro.

Es la ÚNICA fuente de lo que K-nasta dice sobre cómo usar la app (con o sin IA): cada paso describe
algo que existe de verdad (botones y textos reales). Si cambia una pantalla, se cambia aquí.
Los destinos son nombres de ruta («app:nombre»); la capa de servicios los convierte en enlaces.
"""

import re
import unicodedata
from dataclasses import dataclass

TIPOS_VISUAL = frozenset(
    {
        "boton",
        "boton_sec",
        "campo",
        "buscador",
        "opciones",
        "filas",
        "chip",
        "icono",
        "simbolo",
        "casilla",
    }
)


@dataclass(frozen=True)
class Visual:
    """Una mini-pantalla decorativa de un paso (se dibuja con HTML/CSS; no son capturas)."""

    tipo: str
    texto: str = ""  # etiqueta, título o leyenda
    valor: str = ""  # lo que «tiene escrito» un campo o un buscador
    opciones: tuple[str, ...] = ()
    activa: int = 0  # opción marcada (-1: ninguna)
    filas: tuple[tuple[str, str], ...] = ()  # (tienda, precio); la primera se resalta
    variante: str = ""  # positivo | alerta | promo (chips) · camara (buscador)
    icono: str = ""  # id del sprite (tipo «icono»)


@dataclass(frozen=True)
class Paso:
    texto: str
    visuales: tuple[Visual, ...] = ()


def un_paso(texto: str, *visuales: Visual) -> Paso:
    return Paso(texto, tuple(visuales))


def boton(texto: str) -> Visual:
    return Visual("boton", texto)


def boton_sec(texto: str) -> Visual:
    return Visual("boton_sec", texto)


def campo(etiqueta: str, valor: str) -> Visual:
    return Visual("campo", etiqueta, valor)


def buscador(valor: str, camara: bool = False) -> Visual:
    return Visual("buscador", valor=valor, variante="camara" if camara else "")


def opciones(etiqueta: str, *opts: str, activa: int = 0) -> Visual:
    return Visual("opciones", etiqueta, opciones=opts, activa=activa)


def filas(*lineas: tuple[str, str]) -> Visual:
    return Visual("filas", filas=lineas)


def chip(texto: str, variante: str = "") -> Visual:
    return Visual("chip", texto, variante=variante)


def icono(id_icono: str, texto: str) -> Visual:
    return Visual("icono", texto, icono=id_icono)


def simbolo(simbolo_: str, texto: str) -> Visual:
    return Visual("simbolo", simbolo_, valor=texto)


def casilla(texto: str) -> Visual:
    return Visual("casilla", texto)


@dataclass(frozen=True)
class Tema:
    id: str
    titulo: str
    pasos: tuple[Paso, ...]
    acciones: tuple[tuple[str, str], ...]  # (texto del botón, «app:nombre» de la ruta)
    patrones: tuple[tuple[str, int], ...]  # (expresión sobre texto sin tildes, peso)

    @property
    def textos(self) -> list[str]:
        """Los pasos solo como texto (lo que lee la IA y un lector de pantalla)."""
        return [p.texto for p in self.pasos]

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
            un_paso(
                "AhorraPues compara los precios de la canasta familiar entre tiendas de"
                " barrio, minimercados y supermercados de Armenia y el Quindío.",
                icono("i-scale", "Compara precios"),
            ),
            un_paso(
                "Los precios los reporta la comunidad; no vendemos nada ni somos un "
                "sistema oficial.",
                icono("i-user", "Los reporta la comunidad"),
            ),
            un_paso(
                "Para consultar y comparar no necesitas cuenta. La cuenta sirve para "
                "registrar o confirmar precios.",
                chip("Consultar: sin cuenta", "positivo"),
                chip("Registrar: con cuenta"),
            ),
        ],
        [
            ("Ir al inicio", "comparacion:inicio"),
        ],
        [
            ("\\bque es (ahorrapues|esto|esta pagina|la pagina|la app|la plataforma)\\b", 5),  # noqa: E501
            ("\\bpara que sirve\\b", 5),
            ("\\bque (hace|haces|puedes hacer|puedo hacer)\\b", 4),
            ("\\bprimeros pasos\\b|\\bprimera vez\\b|\\btutorial\\b|\\bempezar\\b", 3),
        ],
    ),
    _t(
        "comparar",
        "¿Cómo comparo precios de un producto?",
        [
            un_paso(
                "Escribe el producto en el buscador de la portada (por ejemplo «arroz»)"
                " o entra a «Productos».",
                buscador("arroz"),
            ),
            un_paso(
                "Toca el producto: verás cada tienda con su precio, el precio por kilo "
                "o litro (para comparar empaques de distinto tamaño) y hace cuánto se "
                "reportó.",
                filas(
                    ("Tienda A", "$6.150 /kg"),
                    ("Tienda B", "$6.300 /kg"),
                    ("Tienda C", "$6.350 /kg"),
                ),
            ),
            un_paso(
                "La primera tienda es la de menor precio por unidad. El orden es el "
                "mismo para todos: ninguna tienda paga por salir primero.",
                icono("i-scale", "Mismo orden para todos"),
            ),
            un_paso(
                "Si quieres, filtra por municipio, barrio o rango de precio.",
                opciones("Filtrar por", "Municipio", "Barrio", "Precio", activa=-1),
            ),
        ],
        [
            ("Ver productos", "comparacion:productos"),
        ],
        [
            ("\\bcompar\\w*", 3),
            ("\\bmas barat\\w*", 3),
            ("\\bdonde\\b.{0,40}\\bbarat\\w*", 3),
            ("\\b(tienda|supermercado|minimercado)\\b.{0,30}\\b(barat\\w*|conviene)", 3),  # noqa: E501
            ("\\b(buscar|busco|ver|veo|consultar|consulto)\\b.{0,15}\\bprecios?\\b", 2),  # noqa: E501
        ],
    ),
    _t(
        "cuenta",
        "¿Cómo creo una cuenta?",
        [
            un_paso(
                "Toca «Crear cuenta» (arriba a la derecha).",
                boton("Crear cuenta"),
            ),
            un_paso(
                "Elige un nombre de usuario (de 3 a 30 caracteres) y una contraseña de "
                "8 caracteres o más, que no sea solo números.",
                campo("Nombre de usuario", "maria_l"),
                campo("Contraseña", "••••••••"),
            ),
            un_paso(
                "El correo es opcional: solo sirve para recuperar tu contraseña y no se publica.",
                campo("Correo electrónico (opcional)", "tu@correo.com"),
            ),
            un_paso(
                "Marca la autorización de datos y pulsa «Crear cuenta». Tu nombre nunca"
                " se muestra junto a los precios.",
                casilla("Autorizo el tratamiento de mis datos personales"),
                boton("Crear cuenta"),
            ),
        ],
        [
            ("Crear cuenta", "cuentas:registro"),
            ("Ingresar", "cuentas:ingresar"),
        ],
        [
            ("\\b(crear|creo|abrir|abro|hacer|hago|sacar|saco)\\b.{0,12}\\bcuenta\\b", 4),  # noqa: E501
            ("\\bregistrarme\\b|\\bregistrarse\\b|\\binscrib\\w*|\\bunirme\\b|\\bunirse\\b", 4),  # noqa: E501
            ("\\bregistr(ar|o)\\b(?!.{0,10}\\bprecio)", 2),
            ("\\b(cuenta|usuario|ingresar|iniciar sesion)\\b", 1),
        ],
    ),
    _t(
        "registrar",
        "¿Cómo registro un precio?",
        [
            un_paso(
                "Necesitas una cuenta: ingresa o crea una.",
                boton_sec("Ingresar"),
                boton("Crear cuenta"),
            ),
            un_paso(
                "Toca «Registrar precio». Paso 1: busca el producto o toca uno de la lista.",
                boton("Registrar precio"),
                buscador("arroz"),
            ),
            un_paso(
                "Paso 2: elige la presentación exacta (por ejemplo 500 g o 1 kg), la "
                "tienda donde estás y escribe el precio total del empaque, tal como lo "
                "marca la etiqueta. Pulsa «Guardar precio».",
                opciones("Presentación", "500 g", "1 kg"),
                campo("¿Dónde estás?", "Tienda de la esquina"),
                campo("Precio total del empaque ($)", "8.000"),
                boton("Guardar precio"),
            ),
            un_paso(
                "Atajo: en la comparación de un producto, el botón «Registrar precio "
                "aquí» ya trae el producto y la tienda elegidos.",
                boton("Registrar precio aquí"),
            ),
            un_paso(
                "Tu reporte es anónimo: guardamos tu autoría solo para evitar abusos.",
                icono("i-shield", "Sin tu nombre"),
            ),
        ],
        [
            ("Registrar un precio", "precios:registrar"),
            ("Crear cuenta", "cuentas:registro"),
        ],
        [
            ("\\b(registr|report|sub|anot|agreg|pong|carg)\\w*\\b.{0,25}\\bprecios?\\b", 4),  # noqa: E501
            ("\\bprecios?\\b.{0,25}\\b(registr|report|sub|anot)\\w*", 3),
            ("\\breport(ar|o|e)\\b", 2),
        ],
    ),
    _t(
        "confirmar",
        "¿Cómo confirmo o denuncio un precio?",
        [
            un_paso(
                "Entra a la comparación de un producto con tu cuenta.",
                filas(("Tienda A", "$6.150 /kg"), ("Tienda B", "$6.300 /kg")),
            ),
            un_paso(
                "Si el precio de una tienda sigue igual, toca «Sigue igual»: lo hace "
                "más confiable y lo mantiene vigente.",
                boton_sec("Sigue igual"),
                chip("confirmado hace 1 día", "positivo"),
            ),
            un_paso(
                "Si es incorrecto o abusivo, abre «Denunciar», cuenta el motivo y "
                "envíalo; moderación lo revisa.",
                boton_sec("Denunciar"),
                campo("Motivo", "El precio no coincide"),
            ),
            un_paso(
                "No puedes confirmar ni denunciar los precios que reportaste tú.",
                chip("Este precio lo reportaste tú", "alerta"),
            ),
        ],
        [
            ("Ver productos", "comparacion:productos"),
        ],
        [
            ("\\b(confirm\\w*|sigue igual|denunci\\w*|reclam\\w*)\\b", 4),
            ("\\bprecio\\b.{0,20}\\b(mal|equivocad\\w*|incorrect\\w*|falso|raro)\\b", 3),  # noqa: E501
        ],
    ),
    _t(
        "escanear",
        "¿Cómo busco con la cámara o el código de barras?",
        [
            un_paso(
                "En el buscador de la portada toca el ícono de la cámara y permite el acceso.",
                buscador("Busca arroz, leche, panela…", True),
            ),
            un_paso(
                "Apunta al código de barras del empaque: tu teléfono lo lee solo y te "
                "lleva a la comparación. También puedes escribir el número que está "
                "bajo las barras.",
                icono("i-escanear", "Apunta al código de barras"),
            ),
            un_paso(
                "Si está disponible, también puedes tomar una foto del producto o "
                "elegir una de tu galería para que lo reconozca.",
                icono("i-imagen", "Foto o galería"),
            ),
        ],
        [
            ("Ir al inicio", "comparacion:inicio"),
        ],
        [
            ("\\b(escane\\w*|camara|codigo de barras|barras|foto)\\b", 4),
        ],
    ),
    _t(
        "vigencia",
        "¿Por qué un precio ya no aparece o qué significa «confianza»?",
        [
            un_paso(
                "Un precio se muestra como vigente por 7 días (3 días en productos que "
                "se dañan rápido, como frutas o carnes). Después deja de mostrarse "
                "hasta que alguien lo confirme o registre uno nuevo.",
                chip("hace 2 días · vigente", "positivo"),
                chip("hace 9 días · ya no se muestra", "alerta"),
            ),
            un_paso(
                "«Confianza media» quiere decir que lo reportó una persona; «alta», que"
                " varias personas lo confirmaron o lo publicó el comercio; «baja», que "
                "se aleja de los demás precios y conviene verificarlo.",
                chip("Confianza baja", "alerta"),
                chip("Confianza media"),
                chip("Confianza alta", "positivo"),
            ),
            un_paso(
                "Ayudas a mantenerlos al día con «Sigue igual» o registrando el precio de hoy.",
                boton_sec("Sigue igual"),
                boton("Registrar precio"),
            ),
        ],
        [
            ("Registrar un precio", "precios:registrar"),
        ],
        [
            ("\\b(vigent\\w*|vencid\\w*|venc\\w*|caduc\\w*|desactualizad\\w*)\\b", 4),
            ("\\bconfianza\\b", 4),
            ("\\bya no (aparece|sale|se ve)\\b|\\bpor que no hay precio", 4),
        ],
    ),
    _t(
        "producto_faltante",
        "¿Qué hago si no encuentro un producto?",
        [
            un_paso(
                "Búscalo por nombre o por código de barras; a veces está con otra marca o tamaño.",
                buscador("arroz xyz"),
                chip("Sin resultados", "alerta"),
            ),
            un_paso(
                "Si no está, con tu cuenta toca «Solicitar el producto» y escribe su "
                "nombre, marca y presentación.",
                boton("Solicitar el producto"),
                campo("Nombre", "Arroz integral"),
                campo("Marca", "Diana"),
                boton("Enviar solicitud"),
            ),
            un_paso(
                "Moderación lo revisa y, cuando lo aprueba, ya puedes registrarle precios.",
                chip("En revisión"),
                chip("Aprobado", "positivo"),
            ),
        ],
        [
            ("Solicitar un producto", "catalogo:solicitar"),
            ("Ver productos", "comparacion:productos"),
        ],
        [
            ("\\b(no encuentro|no aparece|no esta|falta|no existe)\\b.{0,20}\\bproducto", 4),  # noqa: E501
            (
                "\\b(agreguen|agregar|anadan|anadir|solicitar|solicito|pedir|pido)\\b.{0,25}\\bproducto",
                4,
            ),  # noqa: E501
            ("\\bproducto\\b.{0,20}\\b(nuevo|no esta|no existe|no aparece)", 3),
        ],
    ),
    _t(
        "tienda_faltante",
        "¿Y si mi tienda no está en el directorio?",
        [
            un_paso(
                "Entra a «Establecimientos» (el directorio de tiendas).",
                boton_sec("Establecimientos"),
            ),
            un_paso(
                "Con tu cuenta, toca «Sugerir establecimiento» y llena el nombre, el "
                "tipo y la dirección.",
                boton("Sugerir establecimiento"),
                campo("Nombre", "Tienda La Esquina"),
                campo("Dirección", "Cra 14 # 10-20"),
                boton("Enviar sugerencia"),
            ),
            un_paso(
                "Moderación lo revisa y, al aprobarlo, ya se pueden registrar precios "
                "en esa tienda.",
                chip("En revisión"),
                chip("Aprobado", "positivo"),
            ),
        ],
        [
            ("Sugerir establecimiento", "establecimientos:sugerir"),
            ("Ver el directorio", "establecimientos:directorio"),
        ],
        [
            (
                "\\b(tienda|establecimiento|local|negocio|supermercado|minimercado)\\b.{0,25}"
                "\\b(no esta|no aparece|falta|nuevo|sugerir|agregar|agrego)",
                4,
            ),  # noqa: E501
            ("\\b(sugerir|sugiero|sugerencia)\\b.{0,25}\\b(tienda|establecimiento|local)", 4),  # noqa: E501
            ("\\bdirectorio\\b", 3),
        ],
    ),
    _t(
        "mis_aportes",
        "¿Dónde veo mis aportes?",
        [
            un_paso(
                "Ingresa a tu cuenta y abre el menú con tu nombre de usuario (arriba a "
                "la derecha; en celular, dentro del menú ☰).",
                boton_sec("tu_usuario ▾"),
            ),
            un_paso(
                "Elige «Mis aportes»: ahí están los precios que has registrado y su estado.",
                boton("Mis aportes"),
                filas(("Arroz · Tienda A", "$6.150"), ("Leche · Tienda B", "$4.200")),
            ),
        ],
        [
            ("Mis aportes", "precios:mis_aportes"),
        ],
        [
            ("\\bmis (aportes|reportes|precios)\\b|\\blo que (he|ya) (reportado|registrado)", 5),  # noqa: E501
        ],
    ),
    _t(
        "apariencia",
        "¿Cómo cambio entre modo claro y oscuro?",
        [
            un_paso(
                "Toca el ícono de sol o luna, arriba a la derecha.",
                simbolo("☀ ☾", "Sol o luna"),
            ),
            un_paso(
                "Cada toque alterna entre claro y oscuro al instante, y la app recuerda tu "
                "elección en este dispositivo.",
                chip("Modo claro"),
                chip("Modo oscuro"),
            ),
        ],
        [],
        [
            ("\\b(modo oscuro|modo claro|oscuro|apariencia|tema)\\b", 5),
        ],
    ),
    _t(
        "comercio",
        "Tengo un comercio: ¿cómo publico mis precios?",
        [
            un_paso(
                "Ingresa con tu cuenta y abre el menú con tu nombre de usuario (arriba a "
                "la derecha; en celular, dentro del menú ☰).",
                boton_sec("tu_usuario ▾"),
            ),
            un_paso(
                "Elige «¿Tienes un comercio?» y crea el perfil de tu negocio.",
                boton("¿Tienes un comercio?"),
            ),
            un_paso(
                "Un moderador verifica el perfil. Cuando está verificado puedes "
                "publicar tus precios oficiales (se muestran como «Oficial») y tus "
                "promociones.",
                chip("En verificación"),
                chip("Verificado", "positivo"),
            ),
            un_paso(
                "Las promociones se señalan, pero no cambian la posición de tu tienda "
                "en la comparación.",
                chip("Oficial", "positivo"),
                chip("Promoción", "promo"),
            ),
        ],
        [
            ("Mi comercio", "comercios:inicio"),
        ],
        [
            ("\\b(tengo|soy|mi|dueno de) (un |una )?(comercio|negocio|tienda)\\b", 3),  # noqa: E501
            ("\\bcomercio\\b", 3),
            ("\\bpublic\\w*\\b.{0,20}\\bprecios?\\b", 3),
        ],
    ),
    _t(
        "privacidad",
        "¿Mis datos son públicos?",
        [
            un_paso(
                "No. Tu reporte es anónimo: nunca se muestra tu nombre, tu usuario, tu "
                "correo ni tu ubicación junto a un precio.",
                icono("i-shield", "Tu nombre no se muestra"),
            ),
            un_paso(
                "Guardamos tu autoría solo para evitar abusos y moderar.",
                chip("Solo para evitar abusos"),
            ),
            un_paso(
                "En «Mis datos» puedes ver qué guardamos y pedir que lo suprimamos. La "
                "política de datos explica todo, incluido el uso de IA.",
                boton("Mis datos"),
                boton_sec("Política de datos"),
            ),
        ],
        [
            ("Política de datos", "cuentas:politica_datos"),
            ("Mis datos", "cuentas:mis_datos"),
        ],
        [
            ("\\b(mis datos|borrar mis datos|eliminar mi cuenta|suprimir)\\b", 4),
            ("\\b(datos|privacidad|anonim\\w*|publicos?)\\b", 3),
        ],
    ),
    _t(
        "contrasena",
        "Olvidé mi contraseña",
        [
            un_paso(
                "En «Ingresar», toca «¿Olvidaste tu contraseña?».",
                boton_sec("Ingresar"),
                chip("¿Olvidaste tu contraseña?"),
            ),
            un_paso(
                "Escribe tu nombre de usuario o tu correo y te enviaremos un enlace "
                "para crear una nueva (solo si registraste un correo).",
                campo("Usuario o correo", "maria_l"),
                boton("Enviar enlace"),
            ),
        ],
        [
            ("Recuperar contraseña", "cuentas:recuperar"),
        ],
        [
            ("\\b(contrasena|clave|password)\\b", 4),
            ("\\bolvide\\b", 2),
        ],
    ),
    _t(
        "canasta",
        "¿Cómo armo mi mercado completo?",
        [
            un_paso(
                "Escríbeme tu lista aquí mismo, por ejemplo: «2 kg arroz, 1 L leche, 12"
                " huevos». También puedes pegarla o adjuntar un archivo.",
                campo("Tu mensaje", "2 kg arroz, 1 L leche, 12 huevos"),
            ),
            un_paso(
                "Te digo en qué tienda te sale más barato comprarlo todo y qué "
                "productos le faltan a las demás.",
                filas(("Tienda A · tiene todo", "$11.041"), ("Tienda B · 2 de 3", "$9.800")),
            ),
            un_paso(
                "Puedes pedirme «menor total», «agrega leche» o «quita el arroz».",
                chip("menor total"),
                chip("agrega leche"),
                chip("quita el arroz"),
            ),
        ],
        [],
        [
            ("\\b(mercado|canasta)\\b", 3),
            ("\\barmar\\b.{0,10}\\blista", 4),
            ("\\bk ?nasta\\b", 3),
        ],
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
