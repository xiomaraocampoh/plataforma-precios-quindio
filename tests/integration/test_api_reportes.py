import uuid

import pytest
from django.urls import reverse

from apps.precios.models import ReportePrecio

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

URL = reverse("api-registrar-reporte")


def _payload(presentacion, establecimiento, precio="4500", **extra):
    return {
        "presentacion": presentacion.pk,
        "establecimiento": establecimiento.pk,
        "precio": precio,
        **extra,
    }


def test_registrar_exige_autenticacion(api, arroz, tiendas):  # M-13
    _, p500, _ = arroz
    respuesta = api.post(URL, _payload(p500, tiendas[0]), format="json")
    assert respuesta.status_code in (401, 403)
    assert ReportePrecio.objects.count() == 0


def test_reportante_registra_precio(api, reportante, arroz, tiendas):
    _, p500, _ = arroz
    api.force_authenticate(reportante)
    respuesta = api.post(URL, _payload(p500, tiendas[0]), format="json")
    assert respuesta.status_code == 201
    assert respuesta.json()["estado"] == "publicado"
    assert ReportePrecio.objects.get().autor == reportante  # trazabilidad M-14


def test_reenvio_offline_con_mismo_id_cliente_no_duplica(api, reportante, arroz, tiendas):  # M-22
    _, p500, _ = arroz
    api.force_authenticate(reportante)
    id_cliente = str(uuid.uuid4())
    for _ in range(3):
        api.post(URL, _payload(p500, tiendas[0], id_cliente=id_cliente), format="json")
    assert ReportePrecio.objects.count() == 1


def test_presentacion_inexistente_es_400_no_500(api, reportante, tiendas):
    api.force_authenticate(reportante)
    payload = {"presentacion": 99999, "establecimiento": tiendas[0].pk, "precio": "4500"}
    assert api.post(URL, payload, format="json").status_code == 400


def test_precio_cero_es_rechazado(api, reportante, arroz, tiendas):  # M-02
    _, p500, _ = arroz
    api.force_authenticate(reportante)
    respuesta = api.post(URL, _payload(p500, tiendas[0], precio="0"), format="json")
    assert respuesta.status_code == 400
