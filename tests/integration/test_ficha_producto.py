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


# --- La ficha va una sola vez; abajo, una fila compacta por establecimiento -------------------
import re  # noqa: E402

from apps.catalogo import services as catalogo  # noqa: E402


@pytest.fixture
def dos_precios(reportante, arroz, tiendas):
    """500 g a $4.500 ($9.000/kg) en una tienda y 1 kg a $8.000 en la otra."""
    prod, p500, p1kg = arroz
    for presentacion, tienda, valor in ((p500, tiendas[0], 4500), (p1kg, tiendas[1], 8000)):
        precios.registrar_reporte(
            autor=reportante,
            presentacion_id=presentacion.pk,
            establecimiento_id=tienda.pk,
            precio=valor,
        )
    return prod


def _filas(html: str) -> list[str]:
    trozos = re.split(r'(?=<li class="tile )', html)
    return [t for t in trozos if t.startswith('<li class="tile tarjeta-precio')]


def test_las_filas_no_repiten_el_nombre_del_producto(client, dos_precios):
    filas = _filas(_ficha(client, dos_precios))
    assert len(filas) == 2
    assert all("Arroz blanco" not in f for f in filas)


def test_cada_fila_trae_tienda_presentacion_precio_y_precio_por_unidad(client, dos_precios):
    primera, segunda = _filas(_ficha(client, dos_precios))
    for texto in ("Súper Quindío", "1 kg", "$8.000", "$8.000 por kg", "Sigue igual"):
        assert texto in primera or texto == "Sigue igual"
    assert "Tienda Doña Rosa" in segunda and "$9.000 por kg" in segunda


def test_la_explicacion_del_precio_por_unidad_aparece_una_sola_vez(client, dos_precios):
    html = _ficha(client, dos_precios)
    assert html.count("para comparar empaques de distinto tamaño") == 1


def test_el_resumen_dice_del_mas_barato_al_mas_caro(client, dos_precios):
    html = _ficha(client, dos_precios)
    assert "del más barato" in html and "$8.000 por kg" in html and "$9.000 por kg" in html


def test_la_foto_aparece_una_sola_vez_aunque_haya_varios_precios(
    client, dos_precios, imagen
):  # EC-01
    catalogo.guardar_foto(dos_precios, catalogo.preparar_foto(imagen()))
    html = _ficha(client, dos_precios)
    assert html.count(f"/productos/{dos_precios.pk}/foto/") == 1
