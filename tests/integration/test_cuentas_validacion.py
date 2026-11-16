"""Ingreso y registro: reglas claras y mensajes que dicen qué hacer (UX de validación)."""

import pytest
from django.urls import reverse

from apps.cuentas.forms import RegistroForm

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

CLAVE_BUENA = "Clave-muy-segura-2026"


def _registro(**cambios) -> RegistroForm:
    datos = {
        "username": "maria.londono",
        "email": "",
        "password1": CLAVE_BUENA,
        "password2": CLAVE_BUENA,
        "acepto_tratamiento_datos": "on",
        **cambios,
    }
    return RegistroForm(datos)


# ───────────── Registro: nombre de usuario ─────────────


@pytest.mark.parametrize("usuario", ["ab c", "ab", "maria@correo.com", "a" * 31, "Mar ía"])
def test_un_nombre_de_usuario_con_formato_invalido_se_rechaza_con_la_regla_completa(usuario):
    form = _registro(username=usuario)
    assert not form.is_valid()
    assert "3 a 30 caracteres" in form.errors["username"][0]
    assert "sin espacios" in form.errors["username"][0]


@pytest.mark.parametrize("usuario", ["maria.londono", "Maria_L-2", "peña", "xyz"])
def test_nombres_de_usuario_validos(usuario):
    assert _registro(username=usuario).is_valid(), _registro(username=usuario).errors


def test_nombre_de_usuario_repetido_dice_que_pruebe_con_otro(reportante):
    form = _registro(username="Reportante1")  # mayúsculas distintas, mismo usuario
    assert not form.is_valid()
    assert form.errors["username"] == ["Ya existe un usuario con ese nombre. Prueba con otro."]


# ───────────── Registro: contraseña ─────────────


def test_clave_debil_y_claves_distintas_se_avisan_a_la_vez():
    form = _registro(password1="12345678", password2="otra-distinta")
    assert not form.is_valid()
    assert "password1" in form.errors  # débil: antes solo se veía cuando coincidían
    assert form.errors["password2"] == ["Las contraseñas no coinciden. Escríbelas de nuevo."]


def test_clave_parecida_al_nombre_de_usuario_se_rechaza():
    form = _registro(username="mariaperez", password1="mariaperez1", password2="mariaperez1")
    assert not form.is_valid()
    assert "password1" in form.errors


# ───────────── Registro: textos de los campos vacíos ─────────────


def test_campos_vacios_dicen_que_hay_que_escribir():
    form = RegistroForm({})
    assert not form.is_valid()
    assert form.errors["username"] == ["Escribe tu nombre de usuario."]
    assert form.errors["password1"] == ["Escribe una contraseña."]
    assert form.errors["password2"] == ["Repite la contraseña para confirmarla."]
    assert "autorización" in form.errors["acepto_tratamiento_datos"][0]
    assert "Ley 1581" in form.errors["acepto_tratamiento_datos"][0]


def test_correo_invalido_da_un_ejemplo():
    form = _registro(email="correo-malo")
    assert not form.is_valid()
    assert form.errors["email"] == ["Escribe un correo válido, por ejemplo nombre@correo.com."]


def test_las_etiquetas_no_llevan_dos_puntos():
    assert _registro().label_suffix == ""


# ───────────── Ingreso ─────────────


def _ingresar(client, **datos):
    return client.post(reverse("cuentas:ingresar"), {"next": "", **datos})


def test_credenciales_incorrectas_dan_un_mensaje_claro_y_conservan_el_usuario(client, reportante):
    r = _ingresar(client, username="reportante1", password="incorrecta")
    html = r.content.decode()
    assert r.status_code == 200
    assert "El usuario o la contraseña no son correctos" in html
    assert "distingue mayúsculas y minúsculas" in html
    assert "Observe que ambos campos" not in html  # el texto por defecto de Django
    assert 'value="reportante1"' in html  # no obliga a reescribir el usuario


def test_ingreso_con_campos_vacios_dice_cual_falta(client):
    html = _ingresar(client, username="", password="").content.decode()
    assert "Escribe tu nombre de usuario." in html
    assert "Escribe tu contraseña." in html


def test_una_cuenta_suspendida_explica_que_esta_desactivada(client, reportante):
    reportante.is_active = False
    reportante.save()
    html = _ingresar(client, username="reportante1", password="clave-segura-123").content.decode()
    assert "Esta cuenta está desactivada" in html
