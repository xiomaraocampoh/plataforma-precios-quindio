"""Entender una lista de mercado escrita a mano (sin IA). Python puro — TDD.

«2 kg arroz», «arroz 2kg», «una docena de huevos», «media libra de café»… Cada línea queda como
(producto, cantidad, unidad). Lo que no se entiende queda vacío: el sistema no inventa cantidades;
usa un valor por defecto o pregunta (EC-14). El texto es un dato: aquí solo se parte y se mide.
"""

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

MAX_LINEAS = 40
CANTIDAD_MAXIMA = Decimal("100000")

_NUMEROS = {
    "un": "1",
    "una": "1",
    "uno": "1",
    "dos": "2",
    "tres": "3",
    "cuatro": "4",
    "cinco": "5",
    "seis": "6",
    "siete": "7",
    "ocho": "8",
    "nueve": "9",
    "diez": "10",
    "media": "0.5",
    "medio": "0.5",
}
# alias → (unidad del sistema, cuántas de ella equivale a 1 del alias)
_UNIDADES = {
    "kilogramos": ("kg", Decimal(1)),
    "kilogramo": ("kg", Decimal(1)),
    "kilos": ("kg", Decimal(1)),
    "kilo": ("kg", Decimal(1)),
    "kg": ("kg", Decimal(1)),
    "kgs": ("kg", Decimal(1)),
    "gramos": ("g", Decimal(1)),
    "gramo": ("g", Decimal(1)),
    "grs": ("g", Decimal(1)),
    "gr": ("g", Decimal(1)),
    "g": ("g", Decimal(1)),
    "libras": ("g", Decimal(500)),
    "libra": ("g", Decimal(500)),
    "lbs": ("g", Decimal(500)),
    "lb": ("g", Decimal(500)),
    "litros": ("L", Decimal(1)),
    "litro": ("L", Decimal(1)),
    "lts": ("L", Decimal(1)),
    "lt": ("L", Decimal(1)),
    "l": ("L", Decimal(1)),
    "mililitros": ("ml", Decimal(1)),
    "mililitro": ("ml", Decimal(1)),
    "ml": ("ml", Decimal(1)),
    "cc": ("ml", Decimal(1)),
    "unidades": ("und", Decimal(1)),
    "unidad": ("und", Decimal(1)),
    "unds": ("und", Decimal(1)),
    "und": ("und", Decimal(1)),
    "docenas": ("und", Decimal(12)),
    "docena": ("und", Decimal(12)),
}
_ALIAS = "|".join(sorted(_UNIDADES, key=len, reverse=True))
_PALABRAS_NUM = "|".join(sorted(_NUMEROS, key=len, reverse=True))
_NUM = rf"(?:\d+(?:[.,]\d+)?|(?:{_PALABRAS_NUM})(?![a-záéíóúñ]))"

_INICIO = re.compile(
    rf"^(?P<num>{_NUM})\s*(?:(?P<uni>{_ALIAS})(?![a-záéíóúñ]))?\s*(?:de\s+)?(?P<producto>.+)$"
)
_FINAL = re.compile(rf"^(?P<producto>.+?)\s+(?P<num>\d+(?:[.,]\d+)?)\s*(?P<uni>{_ALIAS})?$")
_VINETA = re.compile(r"^\s*(?:[-*•·]+|\d+[.)])\s+")
_SEPARADOR = re.compile(r"[\n;]|,(?!\d)")


@dataclass(frozen=True)
class LineaLista:
    producto: str
    cantidad: Decimal | None
    unidad: str | None


def _numero(texto: str) -> Decimal | None:
    crudo = _NUMEROS.get(texto) or texto.replace(",", ".")
    try:
        valor = Decimal(crudo)
    except InvalidOperation:
        return None
    return valor if 0 < valor <= CANTIDAD_MAXIMA else None


def _medida(num: str, alias: str | None) -> tuple[Decimal | None, str | None]:
    valor = _numero(num)
    if valor is None:
        return None, None
    if alias is None:
        return valor, None
    unidad, factor = _UNIDADES[alias]
    total = valor * factor
    return (total if total <= CANTIDAD_MAXIMA else None), unidad


def _limpiar_producto(texto: str) -> str:
    texto = re.sub(r"^(?:de|del)\s+", "", texto.strip())
    return re.sub(r"\s+", " ", texto)


def _linea(trozo: str) -> LineaLista | None:
    texto = re.sub(r"\s+", " ", _VINETA.sub("", trozo).strip().lower())
    if not re.search(r"[a-záéíóúñ]", texto):
        return None
    for patron in (_INICIO, _FINAL):
        m = patron.match(texto)
        if m:
            producto = _limpiar_producto(m.group("producto"))
            if len(producto) < 2 or not re.search(r"[a-záéíóúñ]", producto):
                continue
            cantidad, unidad = _medida(m.group("num"), m.group("uni"))
            return LineaLista(producto, cantidad, unidad)
    return LineaLista(_limpiar_producto(texto), None, None)


def parsear_lista(texto: str) -> list[LineaLista]:
    """Las líneas de una lista de mercado, en el orden escrito (máximo `MAX_LINEAS`)."""
    lineas = []
    for trozo in _SEPARADOR.split(texto or ""):
        linea = _linea(trozo)
        if linea and linea.producto:
            lineas.append(linea)
        if len(lineas) >= MAX_LINEAS:
            break
    return lineas
