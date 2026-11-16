"""Registro sin conexión por el formulario HTMX (RF-12, RNF-15, ADR-009, M-22).

El navegador guarda en localStorage el registro que no pudo enviar y lo reenvía con el mismo
`id_cliente`. El servidor debe tratar ese reenvío como el mismo registro.
"""

import uuid
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.precios.models import ReportePrecio

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

URL = reverse("precios:registrar")
MARCA_GUARDADO = "data-registro-guardado"


def _datos(presentacion, establecimiento, id_cliente, **extra):
    return {
        "establecimiento": establecimiento.pk,
        "presentacion": presentacion.pk,
        "precio": "4500",
        "id_cliente": str(id_cliente),
        **extra,
    }


def test_reenvio_del_formulario_con_mismo_id_cliente_no_duplica(
    client, reportante, arroz, tiendas
):  # M-22
    _, p500, _ = arroz
    client.force_login(reportante)
    datos = _datos(p500, tiendas[0], uuid.uuid4())
    respuestas = [client.post(URL, datos, HTTP_HX_REQUEST="true") for _ in range(3)]
    assert ReportePrecio.objects.count() == 1
    # Cada reenvío confirma el guardado: así la cola del navegador sabe que puede borrarlo
    assert all(MARCA_GUARDADO in r.content.decode() for r in respuestas)


def test_un_formulario_con_errores_no_lleva_la_marca_de_guardado(client, reportante):
    client.force_login(reportante)
    html = client.post(
        URL, {"establecimiento": "", "presentacion": "", "precio": ""}, HTTP_HX_REQUEST="true"
    ).content.decode()
    assert MARCA_GUARDADO not in html


def test_reenvio_conserva_la_fecha_en_que_se_observo_el_precio(
    client, reportante, arroz, tiendas
):  # RN-08: sincronizar horas después no rejuvenece el precio
    _, p500, _ = arroz
    client.force_login(reportante)
    observado = (timezone.now() - timedelta(hours=3)).replace(microsecond=0)
    datos = _datos(p500, tiendas[0], uuid.uuid4(), fecha_observacion=observado.isoformat())
    client.post(URL, datos, HTTP_HX_REQUEST="true")
    assert ReportePrecio.objects.get().fecha_observacion == observado


def test_fecha_de_observacion_vencida_se_rechaza_con_mensaje_visible(
    client, reportante, arroz, tiendas
):  # RN-08
    _, p500, _ = arroz
    client.force_login(reportante)
    vencida = timezone.now() - timedelta(days=30)
    html = client.post(
        URL,
        _datos(p500, tiendas[0], uuid.uuid4(), fecha_observacion=vencida.isoformat()),
        HTTP_HX_REQUEST="true",
    ).content.decode()
    assert ReportePrecio.objects.count() == 0
    assert "ya venció" in html


def test_pagina_de_registro_carga_la_cola_sin_conexion(client, reportante):
    client.force_login(reportante)
    html = client.get(URL).content.decode()
    assert "js/cola-registros.js" in html
    assert f'data-url-registro="{URL}"' in html
    assert 'id="registros-pendientes" role="status" aria-live="polite"' in html
    assert "TODO" not in html


def test_la_cola_no_se_carga_para_visitantes_sin_cuenta(client, db):
    # Sin sesión no hay a quién atribuir el reenvío (M-14)
    html = client.get(reverse("comparacion:inicio")).content.decode()
    assert "js/cola-registros.js" not in html
