"""«Mis aportes» (prioridad C): solo los reportes propios, con su estado."""

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.precios import services
from apps.precios.models import ReportePrecio

pytestmark = pytest.mark.integration


def test_exige_sesion(client):
    r = client.get(reverse("precios:mis_aportes"))
    assert r.status_code == 302
    assert reverse("cuentas:ingresar") in r["Location"]


def test_muestra_solo_los_reportes_propios_con_su_estado(
    client, reportante, django_user_model, arroz, tiendas
):
    _, p500, _ = arroz
    rosa, super_ = tiendas
    otro = django_user_model.objects.create_user(username="otra", password="x-clave-segura-1")
    services.registrar_reporte(
        autor=reportante, presentacion_id=p500.pk, establecimiento_id=rosa.pk, precio=Decimal(2500)
    )
    ajeno = services.registrar_reporte(
        autor=otro, presentacion_id=p500.pk, establecimiento_id=super_.pk, precio=Decimal(2700)
    )
    ReportePrecio.objects.filter(autor=reportante).update(estado=ReportePrecio.Estado.EN_REVISION)
    client.force_login(reportante)
    html = client.get(reverse("precios:mis_aportes")).content.decode()
    assert "Tienda Doña Rosa" in html
    assert "En revisión" in html
    assert ajeno.establecimiento.nombre not in html  # el reporte ajeno no aparece
    assert "Arroz blanco 500 g" in html  # sin notación científica


def test_sin_aportes_invita_a_registrar(client, reportante):
    client.force_login(reportante)
    html = client.get(reverse("precios:mis_aportes")).content.decode()
    assert "Aún no has reportado precios" in html
