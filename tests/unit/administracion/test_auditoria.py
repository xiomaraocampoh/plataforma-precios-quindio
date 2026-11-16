"""Qué cambió en una acción del panel (dominio puro de la auditoría, M-14)."""

from decimal import Decimal

import pytest
from apps.administracion.domain.auditoria import diferencias, valor_auditable

pytestmark = pytest.mark.unit


def test_solo_registra_los_campos_que_cambiaron():
    antes = {"nombre": "Diana", "activa": True}
    despues = {"nombre": "Diana", "activa": False}
    assert diferencias(antes, despues) == {"activa": [True, False]}


def test_al_crear_todo_es_nuevo_y_al_eliminar_todo_desaparece():
    assert diferencias({}, {"nombre": "Roa"}) == {"nombre": [None, "Roa"]}
    assert diferencias({"nombre": "Roa"}, {}) == {"nombre": ["Roa", None]}


def test_sin_cambios_no_hay_diferencias():
    assert diferencias({"nombre": "Roa"}, {"nombre": "Roa"}) == {}


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (Decimal("4.500"), "4.5"),
        (Decimal("500"), "500"),
        (None, None),
        (True, True),
        (7, 7),
        ("texto", "texto"),
        (["b", "a"], ["b", "a"]),
    ],
)
def test_los_valores_se_guardan_en_json_sin_perder_precision(valor, esperado):
    assert valor_auditable(valor) == esperado


def test_un_objeto_se_guarda_por_su_texto():
    class Marca:
        def __str__(self):
            return "Diana"

    assert valor_auditable(Marca()) == "Diana"


@pytest.mark.parametrize("campo", ["password", "email", "first_name", "last_name"])
def test_los_datos_personales_nunca_entran_a_la_bitacora(campo):
    # Ley 1581: la bitácora registra la acción, no los datos del titular
    assert diferencias({campo: "a"}, {campo: "b"}) == {}
