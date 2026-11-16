"""RF-04: búsqueda sin distinguir tildes ni mayúsculas y por código de barras exacto."""

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.catalogo.domain.duplicados import normalizar_nombre
from apps.catalogo.models import Categoria, Presentacion, Producto
from apps.catalogo.selectors import buscar_productos, listar_productos

pytestmark = pytest.mark.integration

EAN = "7702001001234"


@pytest.fixture
def catalogo(db):
    granos = Categoria.objects.create(nombre="Granos")
    abarrotes = Categoria.objects.create(nombre="Abarrotes")

    def crear(nombre, categoria, marca=""):
        return Producto.objects.create(
            nombre=nombre,
            marca=marca,
            nombre_normalizado=normalizar_nombre(nombre),
            categoria=categoria,
        )

    arroz = crear("Arroz blanco", granos, "Diana")
    cafe = crear("Café molido", abarrotes, "Águila Roja")
    pina = crear("Piña en almíbar", abarrotes)
    Presentacion.objects.create(producto=cafe, cantidad=Decimal(250), unidad="g", codigo_barras=EAN)
    return {"arroz": arroz, "cafe": cafe, "pina": pina, "granos": granos}


@pytest.mark.parametrize("texto", ["arroz", "ARROZ", "  Arroz  ", "arroz blanco"])
def test_busca_sin_distinguir_mayusculas(catalogo, texto):
    assert list(buscar_productos(texto)) == [catalogo["arroz"]]


@pytest.mark.parametrize("texto", ["cafe", "CAFÉ", "café molido"])
def test_busca_sin_distinguir_tildes(catalogo, texto):
    assert list(buscar_productos(texto)) == [catalogo["cafe"]]


def test_la_ene_se_conserva(catalogo):
    assert list(buscar_productos("PIÑA")) == [catalogo["pina"]]
    assert list(buscar_productos("pina")) == []  # «pina» y «piña» son palabras distintas


def test_busca_por_marca(catalogo):
    assert list(buscar_productos("diana")) == [catalogo["arroz"]]


def test_busca_por_codigo_de_barras_exacto(catalogo):
    assert list(buscar_productos(EAN)) == [catalogo["cafe"]]
    assert list(buscar_productos(EAN[:-1])) == []  # un código incompleto no coincide


def test_menos_de_dos_letras_no_busca(catalogo):
    assert list(buscar_productos("a")) == []


def test_listado_filtra_por_marca_y_categoria(catalogo):
    assert list(listar_productos(marca="diana")) == [catalogo["arroz"]]
    assert list(listar_productos(categoria_id=catalogo["granos"].pk)) == [catalogo["arroz"]]
    assert set(listar_productos()) == {catalogo["arroz"], catalogo["cafe"], catalogo["pina"]}


def test_sugerencias_del_buscador_usan_la_busqueda_normalizada(client, catalogo):
    html = client.get(reverse("comparacion:sugerencias"), {"q": "CAFE"}).content.decode()
    assert "Café molido" in html


def test_pagina_de_productos_con_filtros(client, catalogo):
    r = client.get(reverse("comparacion:productos"), {"categoria": catalogo["granos"].pk})
    html = r.content.decode()
    assert r.status_code == 200
    assert "Arroz blanco" in html
    assert "Café molido" not in html
    assert '<label for="f-marca">Marca</label>' in html  # cada filtro con etiqueta (WCAG 1.3.1)


def test_pagina_de_productos_devuelve_el_fragmento_con_htmx(client, catalogo):
    r = client.get(reverse("comparacion:productos"), {"q": EAN}, HTTP_HX_REQUEST="true")
    html = r.content.decode()
    assert "<html" not in html
    assert "Café molido" in html
