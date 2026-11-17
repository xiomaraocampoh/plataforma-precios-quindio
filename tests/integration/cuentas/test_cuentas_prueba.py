"""crear_cuentas_prueba: una cuenta por rol, contraseña solo del entorno y 2FA local acotado."""

import secrets
from io import StringIO

import pytest
from django.core.checks import run_checks
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.urls import reverse

from apps.cuentas.domain.cuentas_prueba import CUENTAS_PRUEBA, VARIABLE_CONTRASENA
from apps.cuentas.models import Usuario
from apps.cuentas.views.ingreso import FLAG, PRUEBA_LOCAL

pytestmark = pytest.mark.integration


@pytest.fixture
def clave(monkeypatch):
    valor = secrets.token_urlsafe(16)  # nunca un literal en el código
    monkeypatch.setenv(VARIABLE_CONTRASENA, valor)
    return valor


def _crear() -> str:
    salida = StringIO()
    call_command("crear_cuentas_prueba", stdout=salida)
    return salida.getvalue()


def _ingresar(client, username, clave):
    return client.post(reverse("cuentas:ingresar"), {"username": username, "password": clave})


def _sesion_abierta(client) -> bool:
    return "_auth_user_id" in client.session


# ---------- el comando ----------


def test_sin_la_variable_se_detiene_y_no_crea_nada(db, monkeypatch):
    monkeypatch.delenv(VARIABLE_CONTRASENA, raising=False)
    with pytest.raises(CommandError, match=VARIABLE_CONTRASENA):
        _crear()
    assert not Usuario.objects.filter(es_cuenta_prueba=True).exists()


def test_contrasena_debil_falla_sin_mostrarla(db, monkeypatch):
    monkeypatch.setenv(VARIABLE_CONTRASENA, "1234")
    with pytest.raises(CommandError) as error:
        _crear()
    assert "1234" not in str(error.value)
    assert not Usuario.objects.filter(es_cuenta_prueba=True).exists()  # transacción completa


def test_crea_cada_cuenta_con_su_rol_y_la_tabla_no_muestra_la_contrasena(db, clave):
    salida = _crear()
    assert clave not in salida
    for cuenta in CUENTAS_PRUEBA:
        usuario = Usuario.objects.get(username=cuenta.usuario)
        assert usuario.rol == cuenta.rol
        assert usuario.is_staff is cuenta.staff and usuario.is_superuser is cuenta.superusuario
        assert usuario.is_active is cuenta.activa
        assert usuario.es_cuenta_prueba
        assert usuario.email == cuenta.correo and usuario.email_verificado_en is not None
        assert usuario.acepto_tratamiento_datos and usuario.fecha_aceptacion_datos is not None
        assert usuario.check_password(clave)
        assert cuenta.usuario in salida and cuenta.puede_probar in salida


@pytest.mark.parametrize(
    ("usuario", "grupo", "puede", "no_puede"),
    [
        ("admin_prueba", "Administrador", "cuentas.gestionar_cuentas", None),
        ("moderador_prueba", "Moderador", "moderacion.change_denuncia", "catalogo.add_producto"),
        (
            "editor_prueba",
            "Editor de catálogo",
            "catalogo.add_producto",
            "moderacion.change_denuncia",
        ),
        ("reportante_ana", "Reportante", "precios.add_reporteprecio", "catalogo.add_producto"),
        ("comercio_prueba", None, None, "precios.change_reporteprecio"),
    ],
)
def test_grupos_y_permisos_segun_el_rol(db, clave, usuario, grupo, puede, no_puede):
    _crear()
    cuenta = Usuario.objects.get(username=usuario)
    grupos = set(cuenta.groups.values_list("name", flat=True))
    assert grupos == ({grupo} if grupo else set())  # comercio no tiene grupo (Corte III)
    if puede:
        assert cuenta.has_perm(puede)
    if no_puede:
        assert not cuenta.has_perm(no_puede)


def test_correrlo_otra_vez_actualiza_sin_duplicar(db, clave):
    _crear()
    Usuario.objects.filter(username="editor_prueba").update(rol="reportante", is_active=False)
    salida = _crear()
    assert Usuario.objects.filter(es_cuenta_prueba=True).count() == len(CUENTAS_PRUEBA)
    editor = Usuario.objects.get(username="editor_prueba")
    assert editor.rol == "editor_catalogo" and editor.is_active
    assert editor.groups.filter(name="Editor de catálogo").exists()
    assert "creada" not in salida


def test_la_cuenta_suspendida_no_puede_ingresar(client, db, clave):
    _crear()
    _ingresar(client, "suspendido_prueba", clave)
    assert not _sesion_abierta(client)


# ---------- PERMITIR_PRUEBA_SIN_2FA ----------


@override_settings(DEBUG=True, PERMITIR_PRUEBA_SIN_2FA=True)
def test_en_local_la_cuenta_de_prueba_entra_sin_segundo_paso(client, db, clave):
    _crear()
    r = _ingresar(client, "moderador_prueba", clave)
    assert r.status_code == 302 and r["Location"] != reverse("cuentas:ingresar_verificar")
    assert _sesion_abierta(client) and client.session[FLAG] == PRUEBA_LOCAL
    client.get(reverse("comparacion:inicio"))  # el middleware la deja pasar
    assert _sesion_abierta(client)


@override_settings(DEBUG=False, PERMITIR_PRUEBA_SIN_2FA=True)
def test_con_debug_false_no_se_salta_el_2fa(client, db, clave):
    _crear()
    r = _ingresar(client, "moderador_prueba", clave)
    assert not _sesion_abierta(client)
    assert r["Location"] in (
        reverse("cuentas:ingresar_verificar"),
        reverse("cuentas:ingresar_configurar"),
    )


@override_settings(DEBUG=True, PERMITIR_PRUEBA_SIN_2FA=False)
def test_sin_el_ajuste_tampoco_se_salta(client, db, clave):
    _crear()
    _ingresar(client, "admin_prueba", clave)
    assert not _sesion_abierta(client)


@override_settings(DEBUG=True, PERMITIR_PRUEBA_SIN_2FA=True)
def test_ninguna_otra_cuenta_se_salta_el_2fa(client, django_user_model, clave):
    django_user_model.objects.create_user(
        username="moderadora_real",
        password=clave,
        email="real@example.com",
        rol="moderador",
        is_staff=True,
    )
    _ingresar(client, "moderadora_real", clave)
    assert not _sesion_abierta(client)


def test_si_debug_se_apaga_la_sesion_de_prueba_se_cierra(client, db, clave):
    _crear()
    with override_settings(DEBUG=True, PERMITIR_PRUEBA_SIN_2FA=True):
        _ingresar(client, "admin_prueba", clave)
        assert _sesion_abierta(client)
    with override_settings(DEBUG=False, PERMITIR_PRUEBA_SIN_2FA=True):
        client.get(reverse("comparacion:inicio"))
    assert not _sesion_abierta(client)  # la marca se revisa en cada petición


def test_aviso_en_consola_al_arrancar():
    with override_settings(DEBUG=True, PERMITIR_PRUEBA_SIN_2FA=True):
        assert "cuentas.W001" in {m.id for m in run_checks()}
    with override_settings(DEBUG=False, PERMITIR_PRUEBA_SIN_2FA=True):
        assert "cuentas.W002" in {m.id for m in run_checks()}
    with override_settings(PERMITIR_PRUEBA_SIN_2FA=False):
        assert not {m.id for m in run_checks()} & {"cuentas.W001", "cuentas.W002"}
