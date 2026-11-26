"""Escritura de la canasta: vive en la sesión (sin cuenta) y no toca la base (ADR-0027).

Cada función recibe el mapa de la sesión y lo modifica; la vista decide qué mostrar.
"""

from decimal import Decimal, InvalidOperation

from .domain.canasta import MAX_ITEMS, CanastaInvalidaError

CLAVE_SESION = "canasta_v1"


def leer(sesion) -> list[dict]:
    """La lista guardada: [{producto_id, cantidad (texto), unidad}], en orden de llegada."""
    return list(sesion.get(CLAVE_SESION, []))


def _guardar(sesion, items: list[dict]) -> None:
    sesion[CLAVE_SESION] = items
    sesion.modified = True


def agregar(sesion, producto_id: int, unidad: str) -> None:
    items = leer(sesion)
    if any(i["producto_id"] == producto_id for i in items):
        return  # ya está: agregar dos veces no duplica
    if len(items) >= MAX_ITEMS:
        raise CanastaInvalidaError(f"Una canasta admite hasta {MAX_ITEMS} productos.")
    items.append({"producto_id": producto_id, "cantidad": "1", "unidad": unidad})
    _guardar(sesion, items)


def quitar(sesion, producto_id: int) -> None:
    _guardar(sesion, [i for i in leer(sesion) if i["producto_id"] != producto_id])


def vaciar(sesion) -> None:
    _guardar(sesion, [])


def cambiar(sesion, producto_id: int, cantidad: str, unidad: str, unidades_validas) -> None:
    """Cambia la cantidad y la unidad de un producto. Rechaza lo que no se puede calcular."""
    try:
        valor = Decimal(cantidad.strip().replace(",", "."))
    except (InvalidOperation, AttributeError):
        raise CanastaInvalidaError(
            "Escribe la cantidad con números, por ejemplo 2 o 1,5."
        ) from None
    if not valor.is_finite() or valor <= 0 or valor > Decimal("100000"):
        raise CanastaInvalidaError("La cantidad debe ser mayor que cero.")
    if unidad not in unidades_validas:
        raise CanastaInvalidaError("Esa unidad no sirve para este producto.")
    items = leer(sesion)
    for i in items:
        if i["producto_id"] == producto_id:
            i["cantidad"], i["unidad"] = format(valor.normalize(), "f"), unidad
    _guardar(sesion, items)
