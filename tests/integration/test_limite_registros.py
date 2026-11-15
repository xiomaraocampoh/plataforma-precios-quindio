"""RN-10: un usuario no puede registrar más de N precios por hora (ADR-006 del Consolidado).

El límite vive en el servicio para que aplique igual al formulario HTMX y a la API
(CLAUDE.md §2 regla 3; M-16 resistencia ante reportes masivos, EC-03).
"""

import uuid
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.precios import services
from apps.precios.models import ReportePrecio

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

LIMITE = 3


@pytest.fixture(autouse=True)
def _limite_bajo(settings):
    settings.PRECIOS = {**settings.PRECIOS, "LIMITE_REPORTES_HORA": LIMITE}


def _registrar(autor, presentacion, establecimiento, **extra):
    return services.registrar_reporte(
        autor=autor,
        presentacion_id=presentacion.pk,
        establecimiento_id=establecimiento.pk,
        precio=Decimal("4500"),
        **extra,
    )


def test_servicio_rechaza_el_registro_que_supera_el_limite(reportante, arroz, tiendas):
    _, p500, _ = arroz
    for _ in range(LIMITE):
        _registrar(reportante, p500, tiendas[0])
    with pytest.raises(services.LimiteDeRegistrosExcedidoError):
        _registrar(reportante, p500, tiendas[0])
    assert ReportePrecio.objects.count() == LIMITE


def test_reenvio_idempotente_no_consume_cupo(reportante, arroz, tiendas):  # M-22
    _, p500, _ = arroz
    id_cliente = uuid.uuid4()
    for _ in range(LIMITE + 2):
        _registrar(reportante, p500, tiendas[0], id_cliente=id_cliente)
    assert ReportePrecio.objects.count() == 1


def test_api_responde_429_al_superar_el_limite(api, reportante, arroz, tiendas):
    _, p500, _ = arroz
    for _ in range(LIMITE):
        _registrar(reportante, p500, tiendas[0])
    api.force_authenticate(reportante)
    payload = {"presentacion": p500.pk, "establecimiento": tiendas[0].pk, "precio": "4500"}
    respuesta = api.post(reverse("api-registrar-reporte"), payload, format="json")
    assert respuesta.status_code == 429


def test_formulario_htmx_tambien_respeta_el_limite(client, reportante, arroz, tiendas):
    _, p500, _ = arroz
    for _ in range(LIMITE):
        _registrar(reportante, p500, tiendas[0])
    client.force_login(reportante)
    datos = {"presentacion": p500.pk, "establecimiento": tiendas[0].pk, "precio": "4500"}
    respuesta = client.post(reverse("precios:registrar"), datos, HTTP_HX_REQUEST="true")
    assert respuesta.status_code == 200
    assert "límite" in respuesta.content.decode()
    assert ReportePrecio.objects.count() == LIMITE
