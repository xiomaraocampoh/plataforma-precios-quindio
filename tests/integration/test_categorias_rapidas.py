"""Accesos rápidos por categoría bajo el buscador de la portada."""

import pytest
from django.urls import reverse

from apps.comparacion.selectors import categorias_frecuentes
from apps.precios import services

pytestmark = pytest.mark.django_db


def test_sin_precios_no_hay_accesos_rapidos(client):
    html = client.get(reverse("comparacion:inicio")).content.decode()
    assert "cat-rapidas" not in html


def test_los_accesos_llevan_al_listado_filtrado_y_hay_mas_categorias(
    client, reportante, arroz, tiendas
):
    prod, p500, _ = arroz
    services.registrar_reporte(
        autor=reportante, presentacion_id=p500.pk, establecimiento_id=tiendas[0].pk, precio=4500
    )
    html = client.get(reverse("comparacion:inicio")).content.decode()
    assert f"?categoria={prod.categoria_id}" in html
    assert "Más categorías" in html
    assert categorias_frecuentes()[0].pk == prod.categoria_id
