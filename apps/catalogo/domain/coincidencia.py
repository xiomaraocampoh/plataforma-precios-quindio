"""Qué tanto se parece un producto del catálogo a la pista leída de una foto (ADR-022).

Python puro — TDD. Solo sirve para elegir QUÉ producto abrir; no toca el orden neutral de la
comparación ni los precios (EC-06).

Puntaje (0 a 1):
- con marca en la pista: marca 0,40 + palabras del nombre 0,35 + similitud global 0,15 + bono de
  presentación 0,10;
- sin marca (o con una marca que no está en el catálogo): palabras 0,60 + global 0,30 + bono 0,10.
La marca sola no basta: «Detergente Diana» no debe abrir el arroz Diana.
"""

from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher

from .duplicados import normalizar_nombre, son_posibles_duplicados

UMBRAL_CANDIDATO = 0.45
UMBRAL_MARCA = 0.8  # «Sello Rojo» ≈ «Sello Rojo.» ≈ «Van Camps» / «Van Camp's»
UMBRAL_GLOBAL = 0.6
PALABRAS_VACIAS = frozenset(
    {"de", "del", "la", "las", "el", "los", "y", "x", "con", "en", "para", "pasta", "producto"}
)
_CON_MARCA = (0.40, 0.35, 0.15)
_SIN_MARCA = (0.0, 0.60, 0.30)
_BONO_PRESENTACION = 0.10


def palabras_significativas(texto: str) -> list[str]:
    """Palabras normalizadas (sin tildes ni mayúsculas) sin las palabras vacías, en orden."""
    return [p for p in normalizar_nombre(texto or "").split() if p not in PALABRAS_VACIAS]


def similitud_marca(a: str, b: str) -> float:
    """1 si son iguales; el parecido si es muy alto (≥ 0,8); 0 en otro caso."""
    normal_a, normal_b = normalizar_nombre(a or ""), normalizar_nombre(b or "")
    if not normal_a or not normal_b:
        return 0.0
    if normal_a.replace(" ", "") == normal_b.replace(" ", ""):
        return 1.0
    parecido = SequenceMatcher(None, normal_a, normal_b).ratio()
    return parecido if parecido >= UMBRAL_MARCA else 0.0


def _cantidad(texto: str) -> Decimal | None:
    try:
        valor = Decimal(str(texto).strip().replace(",", "."))
    except (InvalidOperation, ValueError):
        return None
    return valor if valor > 0 else None


def coincide_presentacion(cantidad: str, unidad: str, presentaciones) -> bool:
    """Alguna presentación (cantidad, unidad) tiene la misma cantidad y unidad que la pista."""
    valor, unidad = _cantidad(cantidad), (unidad or "").strip().lower()
    if valor is None or not unidad:
        return False
    return any(Decimal(c) == valor and str(u).lower() == unidad for c, u in presentaciones)


def puntuar_coincidencia(
    pista_nombre: str,
    pista_marca: str,
    pista_cantidad: str,
    pista_unidad: str,
    producto_nombre: str,
    producto_marca: str,
    presentaciones,
) -> float:
    """Puntaje de 0 a 1. `presentaciones` es una lista de (cantidad, unidad) del producto."""
    palabras = palabras_significativas(pista_nombre)
    if not palabras:
        return 0.0
    del_producto = palabras_significativas(producto_nombre)
    peso_marca, peso_palabras, peso_global = _CON_MARCA if pista_marca.strip() else _SIN_MARCA
    presentes = sum(p in del_producto for p in palabras) / len(palabras)
    parecido = son_posibles_duplicados(" ".join(palabras), " ".join(del_producto), UMBRAL_GLOBAL)
    puntaje = (
        peso_marca * similitud_marca(pista_marca, producto_marca)
        + peso_palabras * presentes
        + peso_global * parecido
    )
    if presentes and coincide_presentacion(pista_cantidad, pista_unidad, presentaciones):
        puntaje += _BONO_PRESENTACION
    return round(puntaje, 4)
