"""Qué quiere la persona en un mensaje del chat, sin IA. Python puro — TDD.

Un mensaje es, por defecto, una lista de mercado. Solo se reconocen órdenes cortas y claras
(reiniciar, ordenar, agregar, quitar); si hay duda, es una lista: así una frase de la lista nunca
se confunde con una orden.
"""

import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum

MAX_ORDEN = 60  # una orden es corta; un mensaje largo o con varias líneas es una lista


class Tipo(StrEnum):
    LISTA = "lista"
    REINICIAR = "reiniciar"
    ORDENAR_TOTAL = "ordenar_total"
    ORDENAR_COBERTURA = "ordenar_cobertura"
    AGREGAR = "agregar"
    QUITAR = "quitar"


@dataclass(frozen=True)
class Intencion:
    tipo: Tipo
    resto: str = ""


_REINICIAR = re.compile(
    r"\b(empezar de nuevo|empecemos de nuevo|nueva lista|borrar todo|vaciar|reiniciar|limpiar)\b"
)
_TOTAL = re.compile(r"\b(menor total|mas barato|ordenar por total|solo precio)\b")
_COBERTURA = re.compile(r"\b(mas productos|que tenga todo|cobertura)\b")
_AGREGAR = re.compile(r"^(?:y\s+)?(?:agrega|agregar|anade|anadir|suma|sumar|tambien)\b[:\s]*(.+)$")
_QUITAR = re.compile(r"^(?:quita|quitar|elimina|eliminar|saca|sacar|borra)\b[:\s]*(.+)$")


def _plano(texto: str) -> str:
    base = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in base if not unicodedata.combining(c))


def detectar_intencion(texto: str) -> Intencion:
    original = (texto or "").strip()
    plano = re.sub(r"\s+", " ", _plano(original))
    if not plano or len(plano) > MAX_ORDEN or "\n" in original or ";" in original:
        return Intencion(Tipo.LISTA, original)
    for patron, tipo in (
        (_REINICIAR, Tipo.REINICIAR),
        (_TOTAL, Tipo.ORDENAR_TOTAL),
        (_COBERTURA, Tipo.ORDENAR_COBERTURA),
    ):
        if patron.search(plano) and not re.search(r"\d", plano):
            return Intencion(tipo)
    for patron, tipo in ((_AGREGAR, Tipo.AGREGAR), (_QUITAR, Tipo.QUITAR)):
        if patron.match(plano):
            # el resto se devuelve con el texto original (tildes y mayúsculas) tras la palabra clave
            resto = re.sub(
                r"^(?:y\s+)?\w+\b[:\s]*", "", original, count=1, flags=re.IGNORECASE
            ).strip()
            return Intencion(tipo, resto)
    return Intencion(Tipo.LISTA, original)
