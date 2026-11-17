"""Textos de la tarjeta de un precio (RF-16). Python puro — TDD.

Solo presentación: nada de esto entra en la clave del orden neutral (EC-06). La confianza siempre
lleva texto, no solo color (WCAG 1.4.1).
"""

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

AYUDA_POR_UNIDAD = "para comparar empaques de distinto tamaño"

_FUENTES = {
    "reportante": "Reportado por usuarios",
    "comercio": "Oficial del comercio",
    "sipsa": "Referencia SIPSA",
}
_UNIDADES = {"kg": "kg", "L": "litro", "und": "unidad"}
_CONFIANZA = {
    "alta": "Varias personas lo confirmaron o lo publicó el comercio.",
    "media": "Lo reportó una persona; aún no lo confirma nadie más.",
    "baja": "Se aleja de los demás precios. Verifica antes de ir.",
}


def formatear_pesos(valor: Decimal) -> str:
    """$4.100: pesos sin centavos y con punto de miles (uso colombiano)."""
    if valor < 0:
        raise ValueError("El valor no puede ser negativo.")
    entero = int(valor.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return "$" + f"{entero:,}".replace(",", ".")


def texto_por_unidad(precio_unitario: Decimal, unidad_base: str) -> str:
    try:
        unidad = _UNIDADES[unidad_base]
    except KeyError as exc:
        raise ValueError(f"Unidad base desconocida: {unidad_base}.") from exc
    return f"{formatear_pesos(precio_unitario)} por {unidad}"


def etiqueta_fuente(fuente: str) -> str:
    return _FUENTES.get(fuente, "Fuente sin identificar")


def texto_confianza(nivel: str) -> tuple[str, str]:
    """(título, explicación) del nivel de confianza."""
    try:
        return f"Confianza {nivel}", _CONFIANZA[nivel]
    except KeyError as exc:
        raise ValueError(f"Nivel de confianza desconocido: {nivel}.") from exc


def _plural(n: int, singular: str, plural: str) -> str:
    return f"hace {n} {singular if n == 1 else plural}"


def antiguedad(fecha: datetime, ahora: datetime) -> str:
    """«hace 2 días». Un reloj adelantado (fecha futura) cuenta como «hace un momento»."""
    segundos = max(0, int((ahora - fecha).total_seconds()))
    if segundos < 60:
        return "hace un momento"
    if segundos < 3600:
        return _plural(segundos // 60, "minuto", "minutos")
    if segundos < 86400:
        return _plural(segundos // 3600, "hora", "horas")
    return _plural(segundos // 86400, "día", "días")
