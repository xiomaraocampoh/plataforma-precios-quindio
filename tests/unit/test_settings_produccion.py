"""Ajustes de producción: HTTPS obligatorio por defecto, configurable solo para verificar en local.

Se evalúan en un proceso aparte porque `config.settings.prod` lee el entorno al importarse.
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
    "import json, config.settings.prod as s;"
    "print(json.dumps({"
    "'redirect': s.SECURE_SSL_REDIRECT, 'sesion': s.SESSION_COOKIE_SECURE,"
    "'csrf': s.CSRF_COOKIE_SECURE, 'hsts': s.SECURE_HSTS_SECONDS,"
    "'origenes': getattr(s, 'CSRF_TRUSTED_ORIGINS', None),"
    "'sin_2fa': s.PERMITIR_PRUEBA_SIN_2FA, 'debug': s.DEBUG}))"
)


def _ajustes(**extra: str) -> dict:
    entorno = {k: v for k, v in os.environ.items() if k != "FORZAR_HTTPS"}
    entorno.update(
        DJANGO_SETTINGS_MODULE="config.settings.prod",
        SECRET_KEY="clave-solo-para-esta-prueba",
        REDIS_URL="redis://localhost:6379/0",
        DATABASE_URL="sqlite:///:memory:",
        **extra,
    )
    salida = subprocess.run(  # noqa: S603 — comando fijo, sin entrada de usuario
        [sys.executable, "-c", LEER],
        env=entorno,
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(salida.stdout)


def test_por_defecto_https_es_obligatorio():
    ajustes = _ajustes()
    assert ajustes["redirect"] is True
    assert ajustes["sesion"] is True and ajustes["csrf"] is True
    assert ajustes["hsts"] == 31536000


def test_forzar_https_falso_solo_para_verificar_en_local():
    ajustes = _ajustes(FORZAR_HTTPS="False")
    assert ajustes["redirect"] is False
    assert ajustes["sesion"] is False and ajustes["csrf"] is False
    assert ajustes["hsts"] == 0


def test_los_origenes_de_confianza_csrf_salen_del_entorno():
    ajustes = _ajustes(CSRF_TRUSTED_ORIGINS="https://a.example.com,https://b.example.com")
    assert ajustes["origenes"] == ["https://a.example.com", "https://b.example.com"]


def test_en_produccion_nunca_se_omite_el_2fa_aunque_el_entorno_lo_pida():
    ajustes = _ajustes(PERMITIR_PRUEBA_SIN_2FA="True", DEBUG="True")
    assert ajustes["sin_2fa"] is False
    assert ajustes["debug"] is False


def test_sin_origenes_la_lista_es_vacia():
    assert _ajustes()["origenes"] == []
