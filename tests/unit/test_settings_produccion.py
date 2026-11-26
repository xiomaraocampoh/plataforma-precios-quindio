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


# ---------- Vercel (ADR-0031) sin cambiar Render (ADR-017) ----------

LEER_PLATAFORMA = (
    "import json, config.settings.prod as s;"
    "bd = s.DATABASES['default'];"
    "print(json.dumps({"
    "'hosts': s.ALLOWED_HOSTS, 'origenes': s.CSRF_TRUSTED_ORIGINS,"
    "'conn_max_age': bd['CONN_MAX_AGE'], 'opciones': bd.get('OPTIONS', {}),"
    "'sin_cursores': bd.get('DISABLE_SERVER_SIDE_CURSORS', False),"
    "'cache': s.CACHES['default'], 'correo': s.EMAIL_BACKEND,"
    "'estaticos': s.STORAGES['staticfiles']['BACKEND'], 'wsgi': s.WSGI_APPLICATION}))"
)
POSTGRES_URL = "postgres://u:p@ep-ejemplo-pooler.us-east-1.aws.neon.tech:5432/precios"


def _plataforma(**extra: str) -> subprocess.CompletedProcess:
    excluir = {"FORZAR_HTTPS", "VERCEL", "DOMINIOS_VERCEL", "CONN_MAX_AGE"}
    entorno = {k: v for k, v in os.environ.items() if k not in excluir}
    entorno.update(
        DJANGO_SETTINGS_MODULE="config.settings.prod",
        SECRET_KEY="clave-solo-para-esta-prueba",
        REDIS_URL="redis://localhost:6379/0",
        DATABASE_URL=POSTGRES_URL,
    )
    entorno.update(extra)
    return subprocess.run(  # noqa: S603 — comando fijo, sin entrada de usuario
        [sys.executable, "-c", LEER_PLATAFORMA],
        env=entorno,
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=False,
    )


def _leer(**extra: str) -> dict:
    salida = _plataforma(**extra)
    assert salida.returncode == 0, salida.stderr
    return json.loads(salida.stdout)


def test_en_render_la_conexion_persistente_no_cambia():
    ajustes = _leer()
    assert ajustes["conn_max_age"] == 60
    assert "sslmode" not in ajustes["opciones"]
    assert ajustes["sin_cursores"] is False


def test_en_vercel_la_bd_no_reutiliza_conexiones_y_exige_tls():
    ajustes = _leer(VERCEL="1", CONN_MAX_AGE="600")  # aunque el entorno pida otra cosa
    assert ajustes["conn_max_age"] == 0
    assert ajustes["opciones"]["sslmode"] == "require"
    assert ajustes["sin_cursores"] is True


def test_en_vercel_se_respeta_un_sslmode_mas_estricto_de_la_url():
    ajustes = _leer(VERCEL="1", DATABASE_URL=f"{POSTGRES_URL}?sslmode=verify-full")
    assert ajustes["opciones"]["sslmode"] == "verify-full"


def test_vercel_usa_el_wsgi_y_los_estaticos_con_manifiesto():
    ajustes = _leer(VERCEL="1")
    assert ajustes["wsgi"] == "config.wsgi.application"
    assert ajustes["estaticos"] == "whitenoise.storage.CompressedManifestStaticFilesStorage"


def test_los_dominios_de_vercel_declarados_entran_en_hosts_y_origenes():
    ajustes = _leer(
        VERCEL="1",
        ALLOWED_HOSTS="localhost",
        CSRF_TRUSTED_ORIGINS="https://ahorrapues.co",
        DOMINIOS_VERCEL="ahorrapues.vercel.app,AhorraPues.vercel.app",
    )
    assert ajustes["hosts"] == ["localhost", "ahorrapues.vercel.app"]
    assert ajustes["origenes"] == ["https://ahorrapues.co", "https://ahorrapues.vercel.app"]
    assert not any("*" in h or h.startswith(".") for h in ajustes["hosts"])


def test_un_comodin_en_dominios_vercel_impide_arrancar():
    salida = _plataforma(VERCEL="1", DOMINIOS_VERCEL="*.vercel.app")
    assert salida.returncode != 0
    assert "DOMINIOS_VERCEL" in salida.stderr


def test_la_cache_acepta_redis_con_tls():
    url = "rediss://default:clave@ejemplo.upstash.io:6379"
    ajustes = _leer(VERCEL="1", REDIS_URL=url)
    assert ajustes["cache"]["BACKEND"] == "django.core.cache.backends.redis.RedisCache"
    assert ajustes["cache"]["LOCATION"] == url


def test_con_clave_de_brevo_el_correo_sale_por_la_api_https_tambien_en_vercel():
    ajustes = _leer(VERCEL="1", BREVO_API_KEY="xkeysib-solo-prueba", EMAIL_HOST="smtp.x")
    assert ajustes["correo"] == "anymail.backends.brevo.EmailBackend"
