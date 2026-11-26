"""Ajustes que dependen de la plataforma (ADR-0031): Vercel sin romper Render (ADR-017)."""

import pytest

from core.despliegue import ajustar_bd_serverless, es_vercel, validar_dominios_vercel

pytestmark = pytest.mark.unit

POSTGRES = {"ENGINE": "django.db.backends.postgresql", "NAME": "precios", "CONN_MAX_AGE": 60}


# ---------- ¿Estamos en Vercel? ----------


@pytest.mark.parametrize(
    ("entorno", "esperado"),
    [
        ({"VERCEL": "1"}, True),
        ({"VERCEL": "true"}, True),
        ({}, False),  # Render, Docker y local
        ({"VERCEL": ""}, False),
        ({"VERCEL": "0"}, False),
        ({"VERCEL": "False"}, False),
    ],
)
def test_detecta_vercel_por_la_variable(entorno, esperado):
    assert es_vercel(entorno) is esperado


# ---------- Base de datos serverless ----------


def test_fuera_de_vercel_la_configuracion_no_cambia():
    assert ajustar_bd_serverless(POSTGRES, en_vercel=False) == POSTGRES


def test_en_vercel_cada_invocacion_cierra_su_conexion_y_exige_tls():
    ajustada = ajustar_bd_serverless(POSTGRES, en_vercel=True)
    assert ajustada["CONN_MAX_AGE"] == 0
    assert ajustada["OPTIONS"]["sslmode"] == "require"
    # El pooler de Neon trabaja por transacción: sin cursores del lado del servidor
    assert ajustada["DISABLE_SERVER_SIDE_CURSORS"] is True


def test_no_modifica_el_diccionario_original():
    original = {**POSTGRES, "OPTIONS": {"sslmode": "prefer"}}
    ajustar_bd_serverless(original, en_vercel=True)
    assert original["CONN_MAX_AGE"] == 60
    assert original["OPTIONS"] == {"sslmode": "prefer"}


@pytest.mark.parametrize("debil", ["disable", "allow", "prefer"])
def test_un_sslmode_debil_de_la_url_se_sube_a_require(debil):
    config = {**POSTGRES, "OPTIONS": {"sslmode": debil}}
    assert ajustar_bd_serverless(config, en_vercel=True)["OPTIONS"]["sslmode"] == "require"


@pytest.mark.parametrize("estricto", ["require", "verify-ca", "verify-full"])
def test_un_sslmode_igual_o_mas_estricto_se_respeta(estricto):
    config = {**POSTGRES, "OPTIONS": {"sslmode": estricto, "channel_binding": "require"}}
    opciones = ajustar_bd_serverless(config, en_vercel=True)["OPTIONS"]
    assert opciones == {"sslmode": estricto, "channel_binding": "require"}


def test_sslmode_solo_aplica_a_postgresql():
    sqlite = {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:", "CONN_MAX_AGE": 60}
    ajustada = ajustar_bd_serverless(sqlite, en_vercel=True)
    assert ajustada["CONN_MAX_AGE"] == 0
    assert "sslmode" not in ajustada.get("OPTIONS", {})


# ---------- Dominios *.vercel.app (sin comodines) ----------


def test_acepta_dominios_exactos_de_vercel_y_los_normaliza():
    dominios = [" AhorraPues.vercel.app ", "ahorrapues-git-develop-equipo.vercel.app", ""]
    assert validar_dominios_vercel(dominios) == [
        "ahorrapues.vercel.app",
        "ahorrapues-git-develop-equipo.vercel.app",
    ]


def test_sin_dominios_la_lista_es_vacia():
    assert validar_dominios_vercel([]) == []


def test_quita_duplicados_conservando_el_orden():
    assert validar_dominios_vercel(["a.vercel.app", "b.vercel.app", "a.vercel.app"]) == [
        "a.vercel.app",
        "b.vercel.app",
    ]


@pytest.mark.parametrize(
    "invalido",
    [
        "*.vercel.app",  # comodín abierto: cualquier proyecto de Vercel
        ".vercel.app",  # en ALLOWED_HOSTS equivale a un comodín
        "vercel.app",
        "*",
        "ahorrapues.com",  # los dominios propios van en ALLOWED_HOSTS, no aquí
        "a.b.vercel.app",
        "ahorrapues.vercel.app.evil.com",
        "https://ahorrapues.vercel.app",
        "ahorrapues.vercel.app/",
        "-ahorrapues.vercel.app",
        "ahorra_pues.vercel.app",
    ],
)
def test_rechaza_comodines_y_dominios_que_no_son_de_vercel(invalido):
    with pytest.raises(ValueError, match="DOMINIOS_VERCEL"):
        validar_dominios_vercel([invalido])
