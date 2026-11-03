from decimal import Decimal

import pytest
from django.urls import reverse

from apps.precios import services

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def test_comparacion_es_publica_y_ordena_por_precio_unitario(api, reportante, arroz, tiendas):
    prod, p500, p1kg = arroz
    rosa, super_q = tiendas
    services.registrar_reporte(
        autor=reportante,
        presentacion_id=p500.pk,
        establecimiento_id=rosa.pk,
        precio=Decimal("4500"),
    )  # 9000/kg
    services.registrar_reporte(
        autor=reportante,
        presentacion_id=p1kg.pk,
        establecimiento_id=super_q.pk,
        precio=Decimal("8200"),
    )  # 8200/kg

    respuesta = api.get(reverse("api-comparacion", args=[prod.pk]))

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["criterio_orden"]
    assert [r["establecimiento"] for r in cuerpo["resultados"]] == [
        "Súper Quindío",
        "Tienda Doña Rosa",
    ]


def test_respuesta_publica_no_expone_al_reportante(api, reportante, arroz, tiendas):  # M-15
    prod, p500, _ = arroz
    services.registrar_reporte(
        autor=reportante,
        presentacion_id=p500.pk,
        establecimiento_id=tiendas[0].pk,
        precio=Decimal("4500"),
    )
    texto = api.get(reverse("api-comparacion", args=[prod.pk])).content.decode()
    assert "autor" not in texto
    assert reportante.username not in texto


@pytest.mark.django_db(transaction=True)
def test_nuevo_reporte_invalida_la_cache(api, reportante, arroz, tiendas):  # D-01
    prod, p500, _ = arroz
    url = reverse("api-comparacion", args=[prod.pk])
    assert api.get(url).json()["resultados"] == []
    services.registrar_reporte(
        autor=reportante,
        presentacion_id=p500.pk,
        establecimiento_id=tiendas[0].pk,
        precio=Decimal("4500"),
    )
    assert len(api.get(url).json()["resultados"]) == 1
