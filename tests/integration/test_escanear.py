"""RF-04: escanear un código de barras lleva a la comparación del producto."""

import re
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.catalogo.models import Categoria, Presentacion, Producto
from apps.catalogo.selectors import productos_por_codigo

pytestmark = pytest.mark.integration

EAN = "4006381333931"  # EAN-13 con dígito de control válido


@pytest.fixture
def cafe(db):
    cat = Categoria.objects.create(nombre="Abarrotes")
    producto = Producto.objects.create(
        nombre="Café molido", nombre_normalizado="cafe molido", categoria=cat
    )
    Presentacion.objects.create(
        producto=producto, cantidad=Decimal(250), unidad="g", codigo_barras=EAN
    )
    return producto


def test_selector_encuentra_por_codigo_exacto(cafe):
    assert list(productos_por_codigo(EAN)) == [cafe]


def test_selector_no_repite_producto_con_dos_presentaciones_iguales(cafe):
    Presentacion.objects.create(producto=cafe, cantidad=Decimal(500), unidad="g", codigo_barras=EAN)
    assert list(productos_por_codigo(EAN)) == [cafe]


def test_selector_sin_coincidencia(cafe):
    assert list(productos_por_codigo("96385074")) == []


def test_codigo_conocido_redirige_a_la_comparacion(client, cafe):
    r = client.get(reverse("comparacion:escanear"), {"codigo": EAN})
    assert r.status_code == 302
    assert r.url == reverse("comparacion:comparar", args=[cafe.pk])


def test_codigo_con_espacios_se_normaliza(client, cafe):
    r = client.get(reverse("comparacion:escanear"), {"codigo": " 4006 3813 33931 "})
    assert r.url == reverse("comparacion:comparar", args=[cafe.pk])


def test_codigo_desconocido_ofrece_solicitar_el_producto(client, cafe):
    r = client.get(reverse("comparacion:escanear"), {"codigo": "96385074"})
    assert r.status_code == 200
    html = r.content.decode()
    assert "96385074" in html
    assert reverse("catalogo:solicitar") + "?codigo_barras=96385074" in html


def test_codigo_invalido_explica_el_problema_sin_redirigir(client, cafe):
    r = client.get(reverse("comparacion:escanear"), {"codigo": "4006381333932"})
    assert r.status_code == 200
    assert "no parece un código de barras válido" in r.content.decode()


@pytest.mark.parametrize("codigo", ["", "abc", "<script>alert(1)</script>"])
def test_entrada_basura_no_se_refleja(client, codigo):
    r = client.get(reverse("comparacion:escanear"), {"codigo": codigo})
    assert r.status_code == 200
    assert "<script>alert" not in r.content.decode()


def test_solo_acepta_get(client):
    assert client.post(reverse("comparacion:escanear")).status_code == 405


def test_solicitar_precarga_el_codigo_de_barras(client, django_user_model):
    usuario = django_user_model.objects.create_user(
        username="u1", password="clave-segura-123", acepto_tratamiento_datos=True
    )
    client.force_login(usuario)
    r = client.get(reverse("catalogo:solicitar"), {"codigo_barras": "96385074"})
    assert r.status_code == 200
    assert 'value="96385074"' in r.content.decode()


def test_los_campos_de_archivo_ocultos_del_escaner_tienen_nombre_accesible(client, db):
    # Web:InputWithoutLabelCheck — también el que abre la cámara del sistema
    html = client.get(reverse("comparacion:inicio")).content.decode()
    for campo in re.findall(r"<input[^>]*type=\"file\"[^>]*>", html):
        assert "aria-label=" in campo, campo
