from decimal import Decimal

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.catalogo.models import Categoria, Presentacion, Producto
from apps.establecimientos.models import Establecimiento


@pytest.fixture(autouse=True)
def _limpiar_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def reportante(django_user_model):
    return django_user_model.objects.create_user(
        username="reportante1", password="clave-segura-123", acepto_tratamiento_datos=True
    )


@pytest.fixture
def arroz():
    cat = Categoria.objects.create(nombre="Granos")
    prod = Producto.objects.create(
        nombre="Arroz blanco", nombre_normalizado="arroz blanco", categoria=cat
    )
    p500 = Presentacion.objects.create(producto=prod, cantidad=Decimal("500"), unidad="g")
    p1kg = Presentacion.objects.create(producto=prod, cantidad=Decimal("1"), unidad="kg")
    return prod, p500, p1kg


@pytest.fixture
def tiendas():
    def crear(nombre, tipo):
        return Establecimiento.objects.create(
            nombre=nombre,
            tipo=tipo,
            direccion="Cra 14 # 10-20",
            barrio="Centro",
            latitud=Decimal("4.533889"),
            longitud=Decimal("-75.681111"),
        )

    return crear("Tienda Doña Rosa", "tienda"), crear("Súper Quindío", "supermercado")
