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
def arroz(db):
    cat = Categoria.objects.create(nombre="Granos")
    prod = Producto.objects.create(
        nombre="Arroz blanco", nombre_normalizado="arroz blanco", categoria=cat
    )
    p500 = Presentacion.objects.create(producto=prod, cantidad=Decimal("500"), unidad="g")
    p1kg = Presentacion.objects.create(producto=prod, cantidad=Decimal("1"), unidad="kg")
    return prod, p500, p1kg


@pytest.fixture
def tiendas(db):
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


@pytest.fixture
def imagen():
    """imagen(formato="JPEG", tamano=(800, 600), exif=False) → bytes de una foto de prueba."""

    def crear(formato="JPEG", tamano=(800, 600), color=(200, 40, 40), exif=False) -> bytes:
        from io import BytesIO

        from PIL import Image

        buffer = BytesIO()
        extra = {}
        if exif:  # una foto de celular lleva datos de la cámara (y a veces la ubicación)
            datos = Image.Exif()
            datos[0x010F] = "Camara de prueba"
            datos[0x0132] = "2026:11:19 10:00:00"
            extra["exif"] = datos
        Image.new("RGB", tamano, color).save(buffer, formato, **extra)
        return buffer.getvalue()

    return crear
