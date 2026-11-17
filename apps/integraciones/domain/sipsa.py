"""Interpretación de los valores del CSV de SIPSA (DANE) (RF-07). Python puro — TDD.

El archivo se descarga a mano del sitio del DANE; los precios vienen en formato colombiano.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
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


# ---------- Servicio web SOAP: promediosSipsaCiudad (precio promedio por ciudad) ----------


@dataclass(frozen=True)
class RegistroCiudad:
    ciudad: str
    producto: str
    precio: Decimal
    fecha: date


def limpiar_nombre_sipsa(nombre: str) -> str:
    """El DANE marca algunos productos con «*» («Tomate*», «Piña *»): se quita."""
    return " ".join((nombre or "").replace("*", " ").split())


def registro_desde_campos(campos: dict[str, str]) -> RegistroCiudad:
    """Un <return> del XML (ciudad, producto, precioPromedio, fechaCaptura) → RegistroCiudad."""
    producto = limpiar_nombre_sipsa(campos.get("producto", ""))
    if not producto:
        raise ValueError("Registro sin producto.")
    try:
        precio = Decimal((campos.get("precioPromedio") or "").strip())
    except InvalidOperation:
        raise ValueError(f"Precio no numérico: «{campos.get('precioPromedio')}».") from None
    if not precio.is_finite() or precio <= 0:
        raise ValueError("El precio debe ser positivo.")
    try:
        fecha = date.fromisoformat((campos.get("fechaCaptura") or "")[:10])
    except ValueError:
        raise ValueError(f"Fecha no reconocida: «{campos.get('fechaCaptura')}».") from None
    return RegistroCiudad((campos.get("ciudad") or "").strip(), producto, precio, fecha)


def _misma_ciudad(a: str, b: str) -> bool:
    return " ".join(a.lower().split()) == " ".join(b.lower().split())


def recientes_de_la_ciudad(
    registros: Iterable[RegistroCiudad], *, ciudad: str, dias: int
) -> list[RegistroCiudad]:
    """Los registros de `ciudad` de los últimos `dias` días (contados desde el dato más nuevo).
    Un mismo producto y día repetido conserva el último registro."""
    de_la_ciudad = [r for r in registros if _misma_ciudad(r.ciudad, ciudad)]
    if not de_la_ciudad:
        return []
    desde = max(r.fecha for r in de_la_ciudad) - timedelta(days=dias)
    unicos = {(r.producto, r.fecha): r for r in de_la_ciudad if r.fecha > desde}
    return sorted(unicos.values(), key=lambda r: (r.producto, r.fecha))
