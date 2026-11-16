"""Migración del texto Producto.marca a la entidad Marca, en pasos reversibles y sin perder datos.

0004 crea Marca y la FK temporal · 0005 migra los datos · 0006 quita el texto y renombra la FK.
"""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

pytestmark = [pytest.mark.integration, pytest.mark.django_db(transaction=True)]

ANTES = [("catalogo", "0003_solicitud_catalogo")]
DESPUES = [("catalogo", "0006_quitar_marca_texto")]


def _migrar(destino):
    ejecutor = MigrationExecutor(connection)
    ejecutor.loader.build_graph()
    ejecutor.migrate(destino)
    return MigrationExecutor(connection).loader.project_state(destino).apps


def _al_final():
    ejecutor = MigrationExecutor(connection)
    ejecutor.migrate(ejecutor.loader.graph.leaf_nodes())


@pytest.fixture
def catalogo_con_marcas_en_texto():
    """Productos creados con el esquema anterior (marca como texto libre)."""
    apps = _migrar(ANTES)
    Categoria = apps.get_model("catalogo", "Categoria")
    Producto = apps.get_model("catalogo", "Producto")
    granos = Categoria.objects.create(nombre="Granos")

    def crear(nombre, normal, marca):
        return Producto.objects.create(
            nombre=nombre, nombre_normalizado=normal, marca=marca, categoria=granos
        ).pk

    ids = {
        "arroz": crear("Arroz blanco", "arroz blanco", "Diana"),
        "cafe": crear("Café molido", "cafe molido", "Águila Roja"),
        "cafe_tostado": crear("Café tostado", "cafe tostado", "  aguila   roja "),
        "panela": crear("Panela", "panela", ""),
    }
    yield ids
    _al_final()


def test_el_texto_de_marca_se_convierte_en_una_fk_sin_perder_datos(catalogo_con_marcas_en_texto):
    ids = catalogo_con_marcas_en_texto
    apps = _migrar(DESPUES)
    Producto = apps.get_model("catalogo", "Producto")
    Marca = apps.get_model("catalogo", "Marca")

    assert Marca.objects.count() == 2  # «Águila Roja» y «aguila roja» son la misma marca
    assert Producto.objects.get(pk=ids["arroz"]).marca.nombre == "Diana"
    cafe = Producto.objects.get(pk=ids["cafe"])
    assert cafe.marca.nombre == "Águila Roja"  # se conserva la primera grafía registrada
    assert cafe.marca.nombre_normalizado == "aguila roja"
    assert Producto.objects.get(pk=ids["cafe_tostado"]).marca_id == cafe.marca_id
    assert Producto.objects.get(pk=ids["panela"]).marca_id is None  # sin marca no es una marca
    assert Producto.objects.count() == 4


def test_la_migracion_se_revierte_y_devuelve_el_texto(catalogo_con_marcas_en_texto):
    ids = catalogo_con_marcas_en_texto
    _migrar(DESPUES)
    apps = _migrar(ANTES)
    Producto = apps.get_model("catalogo", "Producto")

    assert Producto.objects.get(pk=ids["arroz"]).marca == "Diana"
    assert Producto.objects.get(pk=ids["cafe"]).marca == "Águila Roja"
    # La variante vuelve con la grafía de la marca unificada; la asociación no se pierde
    assert Producto.objects.get(pk=ids["cafe_tostado"]).marca == "Águila Roja"
    assert Producto.objects.get(pk=ids["panela"]).marca == ""


def test_productos_que_quedarian_duplicados_detienen_la_migracion(catalogo_con_marcas_en_texto):
    apps = _migrar(ANTES)
    Producto = apps.get_model("catalogo", "Producto")
    arroz = Producto.objects.get(nombre_normalizado="arroz blanco")
    duplicado = Producto.objects.create(
        nombre="Arroz Blanco", nombre_normalizado="arroz blanco", marca="DIANA",
        categoria_id=arroz.categoria_id,
    )  # fmt: skip
    with pytest.raises(RuntimeError, match="arroz blanco"):
        _migrar(DESPUES)
    Producto.objects.filter(pk=duplicado.pk).delete()  # deja la BD lista para migrar al final
