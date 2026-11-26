"""Etiqueta de precio de góndola leída por la IA (RF-11 ampliado, ADR-0026). Python puro — TDD.

Lo leído en una etiqueta es un dato NO confiable: el texto impreso puede estar mal leído o pensado
para engañar a la IA. Aquí se valida, se acota y se verifica la consistencia entre el precio, la
cantidad y el precio por unidad impreso. Si algo no cuadra se baja la confianza; nunca se
«corrige» ni se inventa un dato. La promoción es solo una etiqueta (`es_promocion`): no entra en
el orden de la comparación (EC-06).
"""

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from apps.catalogo.domain.codigo_barras import es_gtin_valido, normalizar_codigo
from apps.catalogo.domain.normalizacion import Unidad, a_unidad_base, precio_por_unidad

from .reconocimiento import CONFIANZAS, MAX_MARCA, MAX_NOMBRE, limpiar_texto

PRECIO_MAXIMO_ETIQUETA = Decimal("2000000")  # tope configurable: un precio mayor es absurdo
TOLERANCIA_CONSISTENCIA = Decimal("0.02")  # 2 % entre el precio por unidad impreso y el calculado
CANTIDAD_MAXIMA = Decimal("100000")
MAX_REFERENCIA = 30
MAX_ESTABLECIMIENTO = 80
_CENTAVOS = Decimal("0.01")

_ALIAS_UNIDAD = {
    "g": Unidad.GRAMO,
    "gr": Unidad.GRAMO,
    "grs": Unidad.GRAMO,
    "kg": Unidad.KILOGRAMO,
    "ml": Unidad.MILILITRO,
    "cc": Unidad.MILILITRO,
    "l": Unidad.LITRO,
    "lt": Unidad.LITRO,
    "und": Unidad.UNIDAD,
    "un": Unidad.UNIDAD,
    "unidad": Unidad.UNIDAD,
}
# Unidad de referencia del precio por unidad impreso → (unidad, cuántas de ella)
_REFERENCIAS = {
    "g": (Unidad.GRAMO, Decimal(1)),
    "100g": (Unidad.GRAMO, Decimal(100)),
    "kg": (Unidad.KILOGRAMO, Decimal(1)),
    "ml": (Unidad.MILILITRO, Decimal(1)),
    "100ml": (Unidad.MILILITRO, Decimal(100)),
    "L": (Unidad.LITRO, Decimal(1)),
    "und": (Unidad.UNIDAD, Decimal(1)),
}

_PREFIJO_MONEDA = re.compile(r"^(?:\$|cop)\s*|\s*(?:cop)$", re.IGNORECASE)
_SOLO_NUMERO = re.compile(r"\d+(?:[.,\s]\d+)*")
_MILES = re.compile(r"\d{1,3}(?:[.,]\d{3})+")
_DECIMAL_SIMPLE = re.compile(r"\d+[.,]\d{1,2}")
_REFERENCIA_NO_PERMITIDA = re.compile(r"[^0-9A-Za-z\- ]")
_CANTIDAD = re.compile(r"\d+(?:[.,]\d+)?")


@dataclass(frozen=True)
class EtiquetaPrecio:
    precio: Decimal
    nombre: str
    marca: str
    cantidad: Decimal | None
    unidad: Unidad | None
    precio_anterior: Decimal | None = None  # promoción «antes y ahora»
    es_promocion: bool = False
    precio_por_unidad_impreso: Decimal | None = None  # solo como dato: el que vale se calcula
    unidad_impresa: str = ""
    referencia: str = ""  # SKU o PLU
    codigo_barras: str = ""  # GTIN validado
    establecimiento_texto: str = ""
    confianza: str = "baja"
    consistente: bool | None = None  # None: no hay con qué verificar


def _numero_colombiano(texto: str) -> str | None:
    """«12.900», «12,900», «12 900», «12.900,00», «12,900.00» → «12900» o «12900.00»."""
    texto = re.sub(r"\s+", ".", texto)  # «12 900» se lee igual que «12.900»
    if "." in texto and "," in texto:
        decimal = "," if texto.rfind(",") > texto.rfind(".") else "."
        miles = "." if decimal == "," else ","
        entero, _, fraccion = texto.rpartition(decimal)
        con_miles = rf"\d{{1,3}}(?:{re.escape(miles)}\d{{3}})+|\d+"
        if not re.fullmatch(con_miles, entero) or not re.fullmatch(r"\d{1,2}", fraccion):
            return None
        return entero.replace(miles, "") + "." + fraccion
    if _MILES.fullmatch(texto) and len({c for c in texto if c in ".,"}) == 1:
        return texto.replace(".", "").replace(",", "")
    if _DECIMAL_SIMPLE.fullmatch(texto):
        return texto.replace(",", ".")
    return texto if texto.isdigit() else None


def leer_precio(valor) -> Decimal | None:
    """Precio positivo escrito como en Colombia, o None si no se puede leer sin adivinar."""
    if isinstance(valor, bool):
        return None
    if isinstance(valor, int):
        return Decimal(valor) if valor > 0 else None
    if not isinstance(valor, str):
        return None
    texto = _PREFIJO_MONEDA.sub("", valor.strip()).strip()
    if not texto or not _SOLO_NUMERO.fullmatch(texto):
        return None
    numero = _numero_colombiano(texto)
    if numero is None:
        return None
    precio = Decimal(numero).quantize(_CENTAVOS)
    return precio if precio > 0 else None


def _unidad(valor) -> Unidad | None:
    if not isinstance(valor, str):
        return None
    limpio = valor.strip()
    return Unidad.LITRO if limpio == "L" else _ALIAS_UNIDAD.get(limpio.lower())


def _cantidad(valor) -> Decimal | None:
    if isinstance(valor, bool) or not isinstance(valor, (int, str)):
        return None
    texto = str(valor).strip()
    if not _CANTIDAD.fullmatch(texto):
        return None
    try:
        numero = Decimal(texto.replace(",", "."))
    except InvalidOperation:  # pragma: no cover - el patrón ya lo impide
        return None
    return numero if 0 < numero <= CANTIDAD_MAXIMA else None


def _referencia(valor) -> str:
    texto = limpiar_texto(valor, MAX_REFERENCIA * 2)
    texto = " ".join(_REFERENCIA_NO_PERMITIDA.sub(" ", texto).split())
    return texto[:MAX_REFERENCIA].strip()


def _es_consistente(
    precio: Decimal, cantidad: Decimal, unidad: Unidad, impreso: Decimal, referencia: str
) -> bool:
    """¿El precio por unidad impreso coincide (±2 %) con el que sale del precio y la cantidad?"""
    unidad_ref, cuantas = _REFERENCIAS[referencia]
    calculado, base = precio_por_unidad(precio, cantidad, unidad)
    cantidad_ref_base, base_ref = a_unidad_base(cuantas, unidad_ref)
    if base_ref != base:
        return False
    impreso_por_base = impreso / cantidad_ref_base
    return abs(impreso_por_base - calculado) <= calculado * TOLERANCIA_CONSISTENCIA


def _presentacion(crudo: dict) -> tuple[Decimal | None, Unidad | None]:
    """Cantidad y unidad juntas o ninguna: media presentación no permite calcular nada."""
    unidad, cantidad = _unidad(crudo.get("unidad")), _cantidad(crudo.get("cantidad"))
    return (cantidad, unidad) if unidad is not None and cantidad is not None else (None, None)


def _precio_por_unidad_impreso(crudo: dict) -> tuple[Decimal | None, str]:
    referencia = crudo.get("unidad_precio_por_unidad")
    impreso = leer_precio(crudo.get("precio_por_unidad"))
    return (impreso, referencia) if impreso and referencia in _REFERENCIAS else (None, "")


def _precio_anterior(crudo: dict, precio: Decimal) -> Decimal | None:
    anterior = leer_precio(crudo.get("precio_anterior"))
    return anterior if anterior is not None and anterior > precio else None


def interpretar_etiqueta(
    crudo, *, precio_maximo: Decimal = PRECIO_MAXIMO_ETIQUETA
) -> EtiquetaPrecio | None:
    """Convierte lo leído en una etiqueta segura, o None si no hay un precio y un producto."""
    if not isinstance(crudo, dict):
        return None
    precio = leer_precio(crudo.get("precio"))
    if precio is None or precio > precio_maximo:
        return None
    nombre = limpiar_texto(crudo.get("nombre"), MAX_NOMBRE)
    codigo = normalizar_codigo(str(crudo.get("codigo_barras") or ""))
    codigo = codigo if es_gtin_valido(codigo) else ""
    if not nombre and not codigo:
        return None

    cantidad, unidad = _presentacion(crudo)
    impreso, referencia = _precio_por_unidad_impreso(crudo)
    consistente = None
    if impreso is not None and unidad is not None:
        consistente = _es_consistente(precio, cantidad, unidad, impreso, referencia)
    confianza = crudo.get("confianza") if crudo.get("confianza") in CONFIANZAS else "baja"
    anterior = _precio_anterior(crudo, precio)
    return EtiquetaPrecio(
        precio=precio,
        nombre=nombre,
        marca=limpiar_texto(crudo.get("marca"), MAX_MARCA),
        cantidad=cantidad,
        unidad=unidad,
        precio_anterior=anterior,
        es_promocion=anterior is not None or crudo.get("es_promocion") is True,
        precio_por_unidad_impreso=impreso,
        unidad_impresa=referencia,
        referencia=_referencia(crudo.get("referencia")),
        codigo_barras=codigo,
        establecimiento_texto=limpiar_texto(crudo.get("establecimiento"), MAX_ESTABLECIMIENTO),
        confianza="baja" if consistente is False else confianza,
        consistente=consistente,
    )
