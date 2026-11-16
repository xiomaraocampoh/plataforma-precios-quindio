"""RF-03: «Mis datos»: ver, actualizar y suprimir la cuenta (Ley 1581)."""

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.comparacion.selectors import comparar_producto
from apps.precios import services
from apps.precios.models import ReportePrecio

pytestmark = pytest.mark.integration

CLAVE = "clave-segura-123"  # la de la fixture reportante


def test_exige_sesion(client):
    assert client.get(reverse("cuentas:mis_datos")).status_code == 302
    assert client.get(reverse("cuentas:suprimir")).status_code == 302


def test_muestra_y_actualiza_los_datos(client, reportante):
    client.force_login(reportante)
    html = client.get(reverse("cuentas:mis_datos")).content.decode()
    assert 'value="reportante1"' in html
    r = client.post(reverse("cuentas:mis_datos"), {"username": "reportante1", "email": "r@ex.com"})
    assert r.status_code == 302
    reportante.refresh_from_db()
    assert reportante.email == "r@ex.com"


def test_no_permite_tomar_el_nombre_de_otro_usuario(client, reportante, django_user_model):
    django_user_model.objects.create_user(username="ocupado", password="x-clave-segura-1")
    client.force_login(reportante)
    html = client.post(
        reverse("cuentas:mis_datos"), {"username": "OCUPADO", "email": ""}
    ).content.decode()
    assert "Ya existe un usuario con ese nombre." in html
    assert 'id="id_username_error"' in html  # error asociado al campo (1.3.1)


def test_suprimir_exige_la_contrasena(client, reportante):
    client.force_login(reportante)
    html = client.post(
        reverse("cuentas:suprimir"), {"password": "otra", "confirmo": "on"}
    ).content.decode()
    assert "La contraseña no es correcta." in html
    reportante.refresh_from_db()
    assert reportante.is_active


def test_suprimir_anonimiza_la_cuenta_y_conserva_los_aportes(client, reportante, arroz, tiendas):
    producto, p500, _ = arroz
    rosa, _ = tiendas
    reporte = services.registrar_reporte(
        autor=reportante, presentacion_id=p500.pk, establecimiento_id=rosa.pk, precio=Decimal(2500)
    )
    reportante.email = "r@ex.com"
    reportante.save()
    client.force_login(reportante)

    r = client.post(reverse("cuentas:suprimir"), {"password": CLAVE, "confirmo": "on"})

    assert r.status_code == 302
    reportante.refresh_from_db()
    assert reportante.username.startswith("anonimo-")
    assert reportante.email == ""
    assert not reportante.is_active
    assert not reportante.has_usable_password()
    assert reportante.suprimido_en is not None
    assert ReportePrecio.objects.get(pk=reporte.pk).autor_id == reportante.pk  # aporte conservado
    assert len(comparar_producto(producto.pk)) == 1  # la comparación no pierde el precio
    assert "_auth_user_id" not in client.session  # sesión cerrada
