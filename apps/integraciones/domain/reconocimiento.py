"""Reconocimiento de productos por foto (RF-04, ampliación). Python puro — TDD.

Lo que una IA extrae de una imagen es un dato NO confiable: puede contener texto impreso en el
empaque pensado para engañarla. Por eso aquí se limpia, se acota y se valida, y el resultado
sirve únicamente como texto de búsqueda sobre el catálogo; nunca decide precios ni el orden.
"""

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from apps.catalogo.domain.codigo_barras import es_gtin_valido, normalizar_codigo
from apps.catalogo.domain.normalizacion import Unidad

MAX_BYTES_IMAGEN = 5 * 1024 * 1024
MAX_NOMBRE = 80
MAX_MARCA = 60
CONFIANZAS = frozenset({"alta", "media", "baja"})
_UNIDADES = frozenset(u.value for u in Unidad)
_NO_PERMITIDOS = re.compile(r"[\x00-\x1f\x7f<>{}\[\]`]")
_ESPACIOS = re.compile(r"\s+")


class ImagenInvalidaError(ValueError):
    """El archivo no es una imagen JPEG, PNG o WebP dentro del tamaño permitido."""


@dataclass(frozen=True)
class PistaProducto:
    nombre: str
    marca: str
    cantidad: str
    unidad: str
    codigo_barras: str
    confianza: str


def tipo_de_imagen(datos: bytes, max_bytes: int = MAX_BYTES_IMAGEN) -> str:
    """Tipo MIME según la firma del archivo (no se confía en el nombre ni en el encabezado)."""
    if len(datos) > max_bytes:
        raise ImagenInvalidaError("La imagen es demasiado grande. Prueba con una más liviana.")
    if datos.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if datos.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if datos[:4] == b"RIFF" and datos[8:12] == b"WEBP":
        return "image/webp"
    raise ImagenInvalidaError("Solo se aceptan fotos JPEG, PNG o WebP.")


def _texto(valor, maximo: int) -> str:
    if not isinstance(valor, str):
        return ""
    limpio = _ESPACIOS.sub(" ", _NO_PERMITIDOS.sub(" ", valor)).strip()
    return limpio[:maximo].strip()


def _cantidad(valor) -> str:
    if isinstance(valor, bool) or not isinstance(valor, (int, float, str)):
        return ""
    try:
        numero = Decimal(str(valor).strip().replace(",", "."))
    except InvalidOperation:
        return ""
    if not numero.is_finite() or numero <= 0 or numero > Decimal("100000"):
        return ""
    return format(numero.normalize(), "f")


def interpretar_respuesta(crudo) -> PistaProducto | None:
    """Convierte lo extraído por el modelo en una pista segura, o None si no sirve."""
    if not isinstance(crudo, dict):
        return None
    nombre = _texto(crudo.get("nombre"), MAX_NOMBRE)
    codigo = normalizar_codigo(str(crudo.get("codigo_barras") or ""))
    codigo = codigo if es_gtin_valido(codigo) else ""
    if not nombre and not codigo:
        return None
    unidad = crudo.get("unidad")
    cantidad = _cantidad(crudo.get("cantidad"))
    if unidad not in _UNIDADES or not cantidad:
        cantidad, unidad = "", ""
    confianza = crudo.get("confianza")
    return PistaProducto(
        nombre=nombre,
        marca=_texto(crudo.get("marca"), MAX_MARCA),
        cantidad=cantidad,
        unidad=unidad,
        codigo_barras=codigo,
        confianza=confianza if confianza in CONFIANZAS else "baja",
    )


def consulta_de_busqueda(pista: PistaProducto) -> str:
    """Texto para el buscador del catálogo: nombre y marca, o el código si no hay nombre."""
    return " ".join(p for p in (pista.nombre, pista.marca) if p) or pista.codigo_barras
