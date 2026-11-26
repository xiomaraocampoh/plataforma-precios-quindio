"""Canasta: armar la lista, total por tienda y faltantes (ADR-0027 a 0029; M-24, M-06)."""

from decimal import Decimal

import pytest
from django.core.cache import cache
from django.urls import reverse

from apps.catalogo.models import Categoria, Presentacion, Producto
from apps.precios import services

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _cache_limpia():
    cache.clear()


@pytest.fixture
def leche(db):
    cat = Categoria.objects.create(nombre="Lácteos")
    prod = Producto.objects.create(nombre="Leche", nombre_normalizado="leche", categoria=cat)
    return prod, Presentacion.objects.create(producto=prod, cantidad=Decimal("1"), unidad="L")


def _precio(autor, presentacion, tienda, precio):
    services.registrar_reporte(
        autor=autor, presentacion_id=presentacion.pk, establecimiento_id=tienda.pk, precio=precio
    )


def _agregar(client, producto):
    return client.post(reverse("canasta:agregar"), {"producto_id": producto.pk})


def test_la_pagina_abre_vacia_con_mensaje_amable(client):
    html = client.get(reverse("canasta:inicio")).content.decode()
    assert "Tu canasta está vacía" in html


def test_agregar_un_producto_lo_deja_en_la_lista_y_no_se_duplica(client, arroz):
    prod = arroz[0]
    _agregar(client, prod)
    html = _agregar(client, prod).content.decode()
    assert html.count('name="cantidad"') == 1
    assert "Tu lista" in html


def test_total_por_tienda_con_cantidad_y_unidad(client, reportante, arroz, tiendas):
    prod, _, p1kg = arroz
    rosa, _ = tiendas
    _precio(reportante, p1kg, rosa, 8000)
    _agregar(client, prod)
    client.post(reverse("canasta:cambiar", args=[prod.pk]), {"cantidad": "2,5", "unidad": "kg"})
    html = client.get(reverse("canasta:resultado")).content.decode()
    assert "$20.000" in html  # 2,5 kg × $8.000
    assert "Tienda Doña Rosa" in html and "Más conveniente" in html


def test_un_producto_sin_precio_es_faltante_y_no_se_suma_como_cero(
    client, reportante, arroz, leche, tiendas
):
    # M-24: la tienda sin leche no parece más barata por «sumar cero»
    prod, _, p1kg = arroz
    rosa, super_ = tiendas
    _precio(reportante, p1kg, rosa, 8000)
    _precio(reportante, p1kg, super_, 7000)
    _precio(reportante, leche[1], super_, 4000)
    _agregar(client, prod)
    html = _agregar(client, leche[0]).content.decode()
    assert "Sin precio vigente:</strong> Leche" in html
    assert html.index("Súper Quindío") < html.index("Tienda Doña Rosa")  # la completa va primero
    assert "Tiene todo (2 de 2)" in html and "Tiene 1 de 2" in html


def test_cambiar_el_criterio_a_menor_total_reordena_y_lo_declara(
    client, reportante, arroz, leche, tiendas
):
    prod, _, p1kg = arroz
    rosa, super_ = tiendas
    _precio(reportante, p1kg, rosa, 5000)
    _precio(reportante, p1kg, super_, 7000)
    _precio(reportante, leche[1], super_, 4000)
    _agregar(client, prod)
    _agregar(client, leche[0])
    html = client.get(reverse("canasta:resultado"), {"criterio": "total"}).content.decode()
    assert "Ordenado por: menor total" in html
    assert html.index("Tienda Doña Rosa") < html.index("Súper Quindío")


@pytest.mark.parametrize("cantidad", ["0", "-2", "abc", ""])
def test_cantidad_invalida_se_explica_y_no_se_guarda(client, arroz, cantidad):
    prod = arroz[0]
    _agregar(client, prod)
    r = client.post(
        reverse("canasta:cambiar", args=[prod.pk]), {"cantidad": cantidad, "unidad": "kg"}
    )
    assert 'role="alert"' in r.content.decode()
    assert 'value="1"' in r.content.decode()


def test_unidad_incompatible_se_rechaza(client, arroz):
    prod = arroz[0]
    _agregar(client, prod)
    r = client.post(reverse("canasta:cambiar", args=[prod.pk]), {"cantidad": "1", "unidad": "L"})
    assert "Esa unidad no sirve" in r.content.decode()


def test_quitar_y_vaciar(client, arroz, leche):
    _agregar(client, arroz[0])
    _agregar(client, leche[0])
    html = client.post(reverse("canasta:quitar", args=[arroz[0].pk])).content.decode()
    assert "Leche" in html and 'name="cantidad"' in html
    assert "Tu canasta está vacía" in client.post(reverse("canasta:vaciar")).content.decode()


def test_buscar_ofrece_agregar_y_marca_lo_ya_agregado(client, arroz):
    html = client.get(reverse("canasta:buscar"), {"q": "arroz"}).content.decode()
    assert "Agregar" in html
    _agregar(client, arroz[0])
    assert "En tu canasta" in client.get(reverse("canasta:buscar"), {"q": "arroz"}).content.decode()


def test_la_canasta_no_expone_datos_de_quien_reporto(client, reportante, arroz, tiendas):
    prod, _, p1kg = arroz
    _precio(reportante, p1kg, tiendas[0], 8000)
    _agregar(client, prod)
    html = client.get(reverse("canasta:resultado")).content.decode()
    assert reportante.username not in html  # M-15


def test_el_limite_de_20_productos(client, db):
    cat = Categoria.objects.create(nombre="Varios")
    for n in range(21):
        p = Producto.objects.create(nombre=f"P{n}", nombre_normalizado=f"p{n}", categoria=cat)
        Presentacion.objects.create(producto=p, cantidad=Decimal("1"), unidad="kg")
        html = _agregar(client, p).content.decode()
    assert "hasta 20 productos" in html
