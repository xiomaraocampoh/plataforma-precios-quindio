"""Hallazgos del análisis estático (SonarQube, M-19/M-20) convertidos en pruebas de regresión."""

import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

RAIZ = Path(__file__).resolve().parents[2]


def test_la_redaccion_de_correos_no_se_vuelve_cuadratica_con_texto_largo():
    # python:S8786 — un texto largo sin «@» hacía que la expresión se reintentara desde cada posición.
    from apps.notificaciones.services import _CORREO

    texto = "a" * 60_000
    inicio = time.perf_counter()
    _CORREO.sub("[correo]", texto)
    assert time.perf_counter() - inicio < 0.5


def test_la_redaccion_sigue_ocultando_correos_normales():
    from apps.notificaciones.services import _CORREO

    assert _CORREO.sub("[correo]", "escribe a luisa.askg+x@gmail.com ya") == "escribe a [correo] ya"
    assert _CORREO.sub("[correo]", "ana@sub.dominio.edu.co.") == "[correo]."


def test_el_qr_solo_contiene_svg_y_trazados_aunque_el_texto_sea_hostil():
    # secrets/Web:S5247 — el QR se incrusta con |safe; esto demuestra que no puede inyectar HTML.
    from apps.cuentas.services.segundo_factor import qr_svg

    svg = qr_svg('otpauth://x/<script>alert(1)</script>?a="onload="x')
    assert set(re.findall(r"<([a-zA-Z]+)", svg)) <= {"svg", "path"}
    assert not re.search(r"\son\w+=", svg)


def test_la_configuracion_base_no_trae_la_contrasena_de_la_base_de_datos_en_el_codigo():
    # secrets:S6698 — los secretos van solo por variables de entorno (CLAUDE.md, checklist de seguridad)
    fuente = (RAIZ / "config/settings/base.py").read_text(encoding="utf-8")
    assert "postgres://precios:precios@" not in fuente


def test_sin_database_url_el_arranque_falla_con_un_mensaje_claro():
    entorno = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
    entorno.update(DJANGO_SETTINGS_MODULE="config.settings.base", SECRET_KEY="solo-esta-prueba")
    entorno["DJANGO_READ_DOT_ENV_FILE"] = "False"
    salida = subprocess.run(  # noqa: S603
        [sys.executable, "-c", "import config.settings.base"],
        capture_output=True,
        text=True,
        cwd=RAIZ,
        env=entorno,
        check=False,
    )
    assert salida.returncode != 0 and "DATABASE_URL" in salida.stderr
