"""Interpretación de los valores del CSV de SIPSA (DANE) (RF-07). Python puro — TDD.

El archivo se descarga a mano del sitio del DANE; los precios vienen en formato colombiano.
"""

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

_MILES_CON_PUNTO = re.compile(r"^\d{1,3}(\.\d{3})+$")
FORMATOS_FECHA = ("%Y-%m-%d", "%d/%m/%Y")


def interpretar_precio_cop(texto: str) -> Decimal:
    limpio = texto.replace("$", "").strip()
    if "," in limpio:
        entero, _, decimales = limpio.rpartition(",")
        if "," in entero:
            raise ValueError(f"Precio mal formado: «{texto}».")
        limpio = f"{entero.replace('.', '')}.{decimales}"
    elif _MILES_CON_PUNTO.match(limpio):
        limpio = limpio.replace(".", "")
    try:
        valor = Decimal(limpio)
    except InvalidOperation:
        raise ValueError(f"Precio no numérico: «{texto}».") from None
    if not valor.is_finite() or valor <= 0:
        raise ValueError(f"El precio debe ser positivo: «{texto}».")
    return valor


def interpretar_fecha(texto: str) -> date:
    for formato in FORMATOS_FECHA:
        try:
            return datetime.strptime(texto.strip(), formato).date()  # solo la fecha, sin zona
        except ValueError:
            continue
    raise ValueError(f"Fecha no reconocida (use AAAA-MM-DD o DD/MM/AAAA): «{texto}».")
