"""Ficha tipo catálogo: descripción del producto y sus presentaciones junto a los precios."""

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.precios import services as precios

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def _ficha(client, producto) -> str:
    return client.get(reverse("comparacion:comparar", args=[producto.pk])).content.decode()


def test_la_ficha_muestra_la_descripcion_del_producto(client, arroz):
    prod = arroz[0]
    prod.descripcion = "Grano largo, ideal para el almuerzo diario."
    prod.save()
    assert "Grano largo, ideal para el almuerzo diario." in _ficha(client, prod)


def test_sin_descripcion_no_hay_bloque_vacio(client, arroz):
    assert 'class="ficha-descripcion"' not in _ficha(client, arroz[0])


def test_la_ficha_lista_las_presentaciones_del_producto(client, arroz):
    html = _ficha(client, arroz[0])
    assert 'aria-label="Presentaciones disponibles"' in html


def test_la_descripcion_se_escapa(client, arroz):
    prod = arroz[0]
    prod.descripcion = "<script>alert(1)</script>"
    prod.save()
    assert "<script>alert(1)</script>" not in _ficha(client, prod)


def test_los_precios_siguen_de_menor_a_mayor_precio_por_unidad(
    client, reportante, arroz, tiendas
):  # M-06
    for tienda, valor in zip(tiendas[:2], ("3000", "2500"), strict=True):
        precios.registrar_reporte(
            autor=reportante,
            presentacion_id=arroz[1].pk,
            establecimiento_id=tienda.pk,
            precio=Decimal(valor),
        )
    html = _ficha(client, arroz[0])
    assert html.index("$2.500") < html.index("$3.000")
