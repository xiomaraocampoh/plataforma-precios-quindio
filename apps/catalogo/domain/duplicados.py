"""Normalización de nombres y detección de posibles duplicados (D-05, RF-06, PU-05).

Capa de dominio: Python puro, sin Django. Se desarrolla con TDD.
"""

import re
import unicodedata
from difflib import SequenceMatcher


def normalizar_nombre(nombre: str) -> str:
    sin_marcas = []
    for c in unicodedata.normalize("NFD", nombre.lower()):
        if unicodedata.category(c) == "Mn":
            if c == "̃" and sin_marcas and sin_marcas[-1] == "n":
                sin_marcas.append(c)
            continue
        sin_marcas.append(c)
    texto = unicodedata.normalize("NFC", "".join(sin_marcas))
    texto = re.sub(r"[^\w\s]|_", " ", texto)
    return " ".join(texto.split())


def son_posibles_duplicados(a: str, b: str, umbral: float = 0.85) -> bool:
    if not 0 <= umbral <= 1:
        raise ValueError("El umbral debe estar entre 0 y 1.")
    na, nb = normalizar_nombre(a), normalizar_nombre(b)
    if not na or not nb:
        return False
    return SequenceMatcher(None, na, nb).ratio() >= umbral
