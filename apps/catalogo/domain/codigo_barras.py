"""Códigos de barras GTIN (EAN-8, UPC-A, EAN-13, GTIN-14) — RF-04.

Capa de dominio: Python puro, sin Django. Se desarrolla con TDD.
"""

LONGITUDES_GTIN = frozenset({8, 12, 13, 14})


def normalizar_codigo(crudo: str) -> str:
    """Deja solo los dígitos (los lectores y las personas añaden espacios o guiones)."""
    return "".join(c for c in crudo if c.isascii() and c.isdigit())


def es_gtin_valido(codigo: str) -> bool:
    """Longitud GTIN y dígito de control GS1 (módulo 10). Rechaza el código de solo ceros."""
    if not (codigo.isascii() and codigo.isdigit()) or len(codigo) not in LONGITUDES_GTIN:
        return False
    if int(codigo) == 0:
        return False
    *cuerpo, control = (int(c) for c in codigo)
    # Desde la derecha del cuerpo, los pesos alternan 3, 1, 3, 1…
    suma = sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(cuerpo)))
    return (10 - suma % 10) % 10 == control
