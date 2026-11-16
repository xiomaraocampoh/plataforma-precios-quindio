"""Marca como entidad del catálogo: búsqueda, filtros, API y elementos inactivos."""

from decimal import Decimal

import pytest
from django.db import IntegrityError
from django.urls import reverse

from apps.catalogo import selectors, services
from apps.catalogo.domain.duplicados import normalizar_nombre
from apps.catalogo.models import Categoria, Marca, Presentacion, Producto
from apps.precios.forms import RegistroPrecioForm

pytestmark = pytest.mark.integration


@pytest.fixture
def con_marcas(db):
    granos = Categoria.objects.create(nombre="Granos")
    diana = Marca.objects.create(nombre="Diana")
    roa = Marca.objects.create(nombre="Roa")

    def crear(nombre, marca=None, **extra):
        return Producto.objects.create(
            nombre=nombre,
            nombre_normalizado=normalizar_nombre(nombre),
            marca=marca,
            categoria=granos,
            **extra,
        )

    return {
        "granos": granos,
        "diana": diana,
        "roa": roa,
        "arroz_diana": crear("Arroz blanco", diana),
        "arroz_roa": crear("Arroz blanco", roa),
        "lentejas": crear("Lentejas"),
    }


def test_la_marca_guarda_su_nombre_normalizado_y_no_se_repite(db):
    marca = Marca.objects.create(nombre="  Águila   Roja ")
    assert marca.nombre == "Águila Roja"
    assert marca.nombre_normalizado == "aguila roja"
    with pytest.raises(IntegrityError):
        Marca.objects.create(nombre="AGUILA ROJA")


def test_el_mismo_producto_puede_existir_con_marcas_distintas_pero_no_repetido(con_marcas):
    assert str(con_marcas["arroz_diana"]) == "Arroz blanco Diana"
    with pytest.raises(IntegrityError):
        Producto.objects.create(
            nombre="Lentejas", nombre_normalizado="lentejas", categoria=con_marcas["granos"]
        )  # sin marca también es único


def test_busqueda_y_filtro_por_marca_sin_tildes(con_marcas):
    assert set(selectors.buscar_productos("ROA")) == {con_marcas["arroz_roa"]}
    assert list(selectors.listar_productos(marca="DIANA")) == [con_marcas["arroz_diana"]]
    assert selectors.opciones_de_filtro()["marcas"] == ["Diana", "Roa"]


def test_lo_inactivo_no_se_ofrece_al_publico(con_marcas):
    Marca.objects.filter(pk=con_marcas["roa"].pk).update(activa=False)
    Producto.objects.filter(pk=con_marcas["lentejas"].pk).update(activo=False)
    Categoria.objects.create(nombre="Retirada", activa=False)
    assert "Roa" not in selectors.opciones_de_filtro()["marcas"]
    assert "Retirada" not in [c.nombre for c in selectors.opciones_de_filtro()["categorias"]]
    assert selectors.buscar_productos("lentejas").count() == 0
    assert con_marcas["lentejas"] not in selectors.listar_productos()
    assert selectors.obtener_producto(con_marcas["lentejas"].pk) is None


def test_el_registro_de_precio_no_ofrece_presentaciones_inactivas(con_marcas):
    activa = Presentacion.objects.create(
        producto=con_marcas["arroz_diana"], cantidad=Decimal(500), unidad="g"
    )
    inactiva = Presentacion.objects.create(
        producto=con_marcas["arroz_diana"], cantidad=Decimal(1), unidad="kg", activa=False
    )
    de_producto_inactivo = Presentacion.objects.create(
        producto=con_marcas["lentejas"], cantidad=Decimal(500), unidad="g"
    )
    Producto.objects.filter(pk=con_marcas["lentejas"].pk).update(activo=False)
    opciones = set(RegistroPrecioForm().fields["presentacion"].queryset)
    assert activa in opciones
    assert inactiva not in opciones and de_producto_inactivo not in opciones


def test_la_api_publica_entrega_la_marca_como_texto(api, con_marcas):
    r = api.get(reverse("api-productos"), {"q": "arroz"})
    assert {item["marca"] for item in r.json()["results"]} == {"Diana", "Roa"}
    sin_marca = api.get(reverse("api-productos"), {"q": "lentejas"}).json()["results"][0]
    assert sin_marca["marca"] == ""


def test_aprobar_una_solicitud_reutiliza_la_marca_existente(con_marcas, reportante):
    solicitud = services.solicitar_producto(
        solicitante=reportante,
        nombre="Arroz integral",
        marca="diana",
        categoria_id=con_marcas["granos"].pk,
        cantidad=Decimal(1),
        unidad="kg",
    )
    services.aprobar_solicitud(solicitud_id=solicitud.pk, moderador=reportante)
    assert Producto.objects.get(nombre="Arroz integral").marca == con_marcas["diana"]
    assert Marca.objects.count() == 2
