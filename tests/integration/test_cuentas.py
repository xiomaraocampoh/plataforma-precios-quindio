"""Registro e ingreso de usuarios (Ley 1581: consentimiento expreso)."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.integration

DATOS = {
    "username": "nueva_persona",
    "email": "",
    "password1": "clave-muy-segura-2026",
    "password2": "clave-muy-segura-2026",
    "acepto_tratamiento_datos": "on",
}


def test_registro_crea_usuario_con_consentimiento_y_abre_sesion(client, django_user_model):
    r = client.post(reverse("cuentas:registro"), DATOS)
    assert r.status_code == 302
    u = django_user_model.objects.get(username="nueva_persona")
    assert u.acepto_tratamiento_datos is True
    assert u.fecha_aceptacion_datos is not None
    assert u.rol == "reportante"
    assert "_auth_user_id" in client.session


def test_registro_exige_consentimiento(client, django_user_model):
    datos = {k: v for k, v in DATOS.items() if k != "acepto_tratamiento_datos"}
    r = client.post(reverse("cuentas:registro"), datos)
    assert r.status_code == 200
    assert not django_user_model.objects.filter(username="nueva_persona").exists()


def test_registro_rechaza_claves_distintas(client, django_user_model):
    r = client.post(reverse("cuentas:registro"), {**DATOS, "password2": "otra-clave-distinta"})
    assert r.status_code == 200
    assert not django_user_model.objects.filter(username="nueva_persona").exists()


def test_registro_rechaza_usuario_repetido(client, reportante):
    r = client.post(reverse("cuentas:registro"), {**DATOS, "username": reportante.username})
    assert r.status_code == 200
    assert b"Ya existe" in r.content


def test_ingreso_y_salida(client, reportante):
    r = client.post(
        reverse("cuentas:ingresar"), {"username": "reportante1", "password": "clave-segura-123"}
    )
    assert r.status_code == 302
    assert "_auth_user_id" in client.session
    assert client.post(reverse("cuentas:salir")).status_code == 302
    assert "_auth_user_id" not in client.session


def test_registrar_precio_redirige_al_ingreso_de_la_plataforma(client):
    r = client.get(reverse("precios:registrar"))
    assert r.status_code == 302
    assert r["Location"].startswith(reverse("cuentas:ingresar"))
