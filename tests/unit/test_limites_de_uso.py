"""Límites de uso de la API (M-16): los valores por defecto no cambian; solo se suben a propósito.

Subirlos es necesario únicamente para la prueba de carga (k6 simula 500 personas desde UNA sola
dirección IP, y el límite es por IP). Se evalúan en un proceso aparte porque se leen al importar.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

RAIZ = Path(__file__).resolve().parents[2]
LEER = (
    "import json, config.settings.base as s;"
    "t = s.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'];"
    "print(json.dumps({k: t[k] for k in ('anon', 'user', 'reportes')}))"
)


def _tasas(**extra: str) -> dict:
    entorno = {k: v for k, v in os.environ.items() if not k.startswith("LIMITE_")}
    entorno.update(DJANGO_SETTINGS_MODULE="config.settings.base", SECRET_KEY="solo-esta-prueba")
    entorno.update(extra)
    salida = subprocess.run(  # noqa: S603
        [sys.executable, "-c", LEER],
        capture_output=True,
        text=True,
        cwd=RAIZ,
        env=entorno,
        check=True,
    )
    return json.loads(salida.stdout.strip().splitlines()[-1])


def test_los_limites_por_defecto_son_los_de_siempre():
    assert _tasas() == {"anon": "120/min", "user": "240/min", "reportes": "30/hour"}


def test_se_pueden_subir_los_limites_de_lectura_para_la_prueba_de_carga():
    tasas = _tasas(LIMITE_ANONIMO="1000000/min", LIMITE_USUARIO="1000000/min")
    assert tasas["anon"] == "1000000/min" and tasas["user"] == "1000000/min"


def test_el_limite_de_escritura_no_se_toca_con_los_de_lectura():
    # Subir la lectura para k6 no debe relajar nunca el límite de registros (M-13, RN-10)
    assert _tasas(LIMITE_ANONIMO="1000000/min")["reportes"] == "30/hour"
