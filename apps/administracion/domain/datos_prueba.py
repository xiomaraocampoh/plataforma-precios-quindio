"""Lectura de las filas CSV de los datos de prueba (data/demo/). Python puro — TDD.

Cada función recibe texto tal como viene del CSV y devuelve el valor ya validado, o lanza
`FilaInvalidaError` con un mensaje que nombra el campo. El servicio añade el archivo y la línea.
Las reglas de negocio (vigencia, anomalías, duplicados) NO se repiten aquí: se aplican al cargar,
con los mismos servicios que usa la aplicación.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from apps.catalogo.domain.codigo_barras import es_gtin_valido

UNIDADES = {"g": "g", "kg": "kg", "ml": "ml", "l": "L", "und": "und"}
TIPOS = frozenset({"supermercado", "discount", "minimercado", "tienda", "plaza"})
# «oficial» = el precio que publica el propio comercio; en el dominio de precios es «comercio»
FUENTES = {"reportante": "reportante", "oficial": "comercio"}
_NUMERO = re.compile(r"^\d+(\.\d+)?$")
_SI = frozenset({"si", "sí", "s", "true", "1"})
_NO = frozenset({"no", "n", "false", "0", ""})


class FilaInvalidaError(ValueError):
    """Un valor del CSV no cumple el formato esperado."""


def _texto(fila: dict, campo: str, *, obligatorio: bool = True) -> str:
    valor = " ".join((fila.get(campo) or "").split())
    if obligatorio and not valor:
        raise FilaInvalidaError(f"El campo «{campo}» es obligatorio.")
    return valor


def _positivo(texto: str, campo: str) -> Decimal:
    limpio = (texto or "").strip()
    if not _NUMERO.match(limpio):
        raise FilaInvalidaError(f"El campo «{campo}» debe ser un número positivo: «{texto}».")
    try:
        valor = Decimal(limpio)
    except InvalidOperation as exc:  # pragma: no cover — la expresión regular ya lo impide
        raise FilaInvalidaError(f"El campo «{campo}» no es un número: «{texto}».") from exc
    if valor <= 0:
        raise FilaInvalidaError(f"El campo «{campo}» debe ser mayor que cero.")
    return valor


def leer_precio(texto: str) -> Decimal:
    """Pesos colombianos con punto decimal opcional y sin separador de miles («4100»)."""
    return _positivo(texto, "precio")


def leer_cantidad(texto: str) -> Decimal:
    return _positivo(texto, "cantidad")


def leer_unidad(texto: str) -> str:
    unidad = UNIDADES.get((texto or "").strip().lower())
    if unidad is None:
        raise FilaInvalidaError(f"La unidad «{texto}» no existe; usa g, kg, ml, L o und.")
    return unidad


def leer_fuente(texto: str) -> str:
    fuente = FUENTES.get((texto or "").strip().lower())
    if fuente is None:
        raise FilaInvalidaError(f"La fuente «{texto}» no existe; usa reportante u oficial.")
    return fuente


def leer_si_no(texto: str, *, campo: str) -> bool:
    valor = (texto or "").strip().lower()
    if valor in _SI:
        return True
    if valor in _NO:
        return False
    raise FilaInvalidaError(f"El campo «{campo}» debe ser «si» o «no»: «{texto}».")


def _entero_no_negativo(texto: str, campo: str) -> int:
    limpio = (texto or "").strip() or "0"
    if not limpio.isdigit():
        raise FilaInvalidaError(f"El campo «{campo}» debe ser un entero ≥ 0: «{texto}».")
    return int(limpio)


def fecha_de_observacion(ahora: datetime, *, dias: str, horas: str) -> datetime:
    """La fecha se guarda relativa («hace N días») para que el conjunto no envejezca."""
    return ahora - timedelta(
        days=_entero_no_negativo(dias, "días atrás"),
        hours=_entero_no_negativo(horas, "horas atrás"),
    )


@dataclass(frozen=True)
class FilaPresentacion:
    producto: str
    marca: str
    cantidad: Decimal
    unidad: str
    codigo_barras: str


def leer_presentacion(fila: dict) -> FilaPresentacion:
    codigo = _texto(fila, "codigo_barras", obligatorio=False)
    if codigo and not es_gtin_valido(codigo):
        raise FilaInvalidaError(f"El código de barras «{codigo}» no es un GTIN válido.")
    return FilaPresentacion(
        producto=_texto(fila, "producto"),
        marca=_texto(fila, "marca"),
        cantidad=leer_cantidad(fila.get("cantidad", "")),
        unidad=leer_unidad(fila.get("unidad", "")),
        codigo_barras=codigo,
    )


@dataclass(frozen=True)
class FilaEstablecimiento:
    nombre: str
    tipo: str
    direccion: str
    barrio: str
    municipio: str
    ficticia: bool


def leer_establecimiento(fila: dict) -> FilaEstablecimiento:
    tipo = _texto(fila, "tipo").lower()
    if tipo not in TIPOS:
        raise FilaInvalidaError(f"El tipo «{tipo}» no existe; usa uno de {sorted(TIPOS)}.")
    return FilaEstablecimiento(
        nombre=_texto(fila, "nombre"),
        tipo=tipo,
        direccion=_texto(fila, "direccion"),
        barrio=_texto(fila, "barrio", obligatorio=False),
        municipio=_texto(fila, "municipio"),
        ficticia=leer_si_no(fila.get("ficticia", ""), campo="ficticia"),
    )
