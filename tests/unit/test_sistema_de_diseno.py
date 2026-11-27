"""Sistema de diseño: toda acción suelta es un botón; el texto subrayado es solo para enlaces en frases.

Si una acción se ve como un enlace con flecha («Ver en el mapa ›»), la persona no sabe que es un
botón y la app se ve inconsistente. Esta prueba revisa las plantillas para que no vuelva a pasar.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

RAIZ = Path(__file__).resolve().parents[2]
PLANTILLAS = [*RAIZ.glob("apps/*/templates/**/*.html"), *RAIZ.glob("templates/**/*.html")]
CLASES = re.compile(r'class="([^"]*)"')


def _clases(texto: str):
    for m in CLASES.finditer(texto):
        yield m.start(), set(m.group(1).split())


def _linea(texto: str, pos: int) -> int:
    return texto.count("\n", 0, pos) + 1


def _infracciones(prohibida=None, exige_btn=None):
    salida = []
    for ruta in PLANTILLAS:
        texto = ruta.read_text(encoding="utf-8")
        for pos, clases in _clases(texto):
            if prohibida and prohibida in clases:
                salida.append(f"{ruta.relative_to(RAIZ)}:{_linea(texto, pos)} usa «{prohibida}»")
            if exige_btn and exige_btn in clases and "btn" not in clases:
                salida.append(
                    f"{ruta.relative_to(RAIZ)}:{_linea(texto, pos)} «{exige_btn}» sin btn"
                )
    return salida


def test_hay_plantillas_que_revisar():
    assert len(PLANTILLAS) > 40


@pytest.mark.parametrize("clase", ["enlace-flecha", "btn-texto"])
def test_no_quedan_acciones_con_estilo_de_enlace(clase):
    assert _infracciones(prohibida=clase) == []


@pytest.mark.parametrize("clase", ["tp-mapa", "ir"])
def test_los_accesos_a_otra_pantalla_son_botones_del_sistema(clase):
    assert _infracciones(exige_btn=clase) == []
