"""Normalización de nombres y detección de posibles duplicados (D-05, RF-06, PU-05).

Capa de dominio: Python puro, sin Django. Se desarrolla con TDD.

Regla D-05: el nombre se compara en minúsculas, sin tildes salvo la ñ, sin puntuación ni
espacios dobles; dos nombres con similitud ≥ 0,85 se señalan al moderador como posibles
duplicados. La decisión final es humana: aquí solo se marca.
"""

import re
import unicodedata
from difflib import SequenceMatcher

UMBRAL_DUPLICADO = 0.85
_TILDE_DE_LA_ENE = "̃"  # marca combinante que forma la ñ en NFD
_PUNTUACION = re.compile(r"[^\w\s]|_")


def _quitar_tildes_salvo_ene(texto: str) -> str:
    conservados: list[str] = []
    for caracter in unicodedata.normalize("NFD", texto):
        es_marca = unicodedata.category(caracter) == "Mn"
        forma_ene = caracter == _TILDE_DE_LA_ENE and conservados[-1:] in (["n"], ["N"])
        if not es_marca or forma_ene:
            conservados.append(caracter)
    return unicodedata.normalize("NFC", "".join(conservados))


def normalizar_nombre(nombre: str) -> str:
    """Forma canónica de un nombre de producto para compararlo (D-05)."""
    texto = _quitar_tildes_salvo_ene(nombre.lower())
    return " ".join(_PUNTUACION.sub(" ", texto).split())


def son_posibles_duplicados(a: str, b: str, umbral: float = UMBRAL_DUPLICADO) -> bool:
    """True si los nombres normalizados se parecen al menos `umbral` (0 a 1)."""
    if not 0 <= umbral <= 1:
        raise ValueError("El umbral debe estar entre 0 y 1.")
    normal_a, normal_b = normalizar_nombre(a), normalizar_nombre(b)
    if not normal_a or not normal_b:
        return False  # sin texto no hay base de comparación
    return SequenceMatcher(None, normal_a, normal_b).ratio() >= umbral
