"""¿Qué tienda del directorio es la que nombra una etiqueta de precio? (ADR-0026). Python puro.

Solo se propone una tienda si la coincidencia es única; ante la duda no se propone ninguna y la
persona elige. Esta regla nunca crea tiendas: el directorio lo modera una persona (RF-09).
"""

from collections.abc import Iterable

from apps.catalogo.domain.duplicados import normalizar_nombre, son_posibles_duplicados

MIN_CARACTERES = 3  # «D1» solo no basta para distinguir una sede
MIN_CARACTERES_PARCIAL = 4  # un texto contenido en el nombre («Mercacentro») debe ser específico


def _contiene(mayor: str, menor: str) -> bool:
    """`menor` aparece en `mayor` como palabras completas («rosa» no está en «rosado»)."""
    return f" {menor} " in f" {mayor} "


def _coincide(texto: str, nombre: str) -> bool:
    return (
        _contiene(texto, nombre)
        or (len(texto) >= MIN_CARACTERES_PARCIAL and _contiene(nombre, texto))
        or son_posibles_duplicados(texto, nombre)
    )


def elegir_establecimiento(texto, candidatos: Iterable[tuple[int, str]]) -> int | None:
    """El id del único establecimiento que coincide con el texto, o None si ninguno o varios."""
    if not isinstance(texto, str):
        return None
    normal = normalizar_nombre(texto)
    if len(normal) < MIN_CARACTERES:
        return None
    nombres = [(pk, normalizar_nombre(nombre)) for pk, nombre in candidatos]
    exactos = [pk for pk, nombre in nombres if nombre == normal]
    if len(exactos) == 1:
        return exactos[0]
    parecidos = [pk for pk, nombre in nombres if nombre and _coincide(normal, nombre)]
    return parecidos[0] if len(parecidos) == 1 else None
