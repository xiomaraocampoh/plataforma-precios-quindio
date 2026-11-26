"""El departamento de cada categoría: campo, restricción, migración y semilla."""

import pytest
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor

from apps.catalogo.domain.grupos import GRUPOS
from apps.catalogo.models import Categoria

pytestmark = pytest.mark.django_db


def test_las_opciones_del_modelo_son_las_del_dominio():
    assert [v for v, _ in Categoria.Grupo.choices] == [g.valor for g in GRUPOS]
    assert [e for _, e in Categoria.Grupo.choices] == [g.etiqueta for g in GRUPOS]


def test_una_categoria_nueva_sin_departamento_es_otros():
    assert Categoria.objects.create(nombre="Rarezas").grupo == "otros"


def test_la_base_rechaza_un_departamento_inventado():
    with pytest.raises(IntegrityError), transaction.atomic():
        Categoria.objects.create(nombre="X", grupo="no-existe")


def test_str_no_cambia():
    assert str(Categoria.objects.create(nombre="Arroz", grupo="mercado")) == "Arroz"


@pytest.mark.django_db(transaction=True)
def test_la_migracion_asigna_el_departamento_a_las_categorias_existentes():
    ejecutor = MigrationExecutor(connection)
    antes = [("catalogo", "0010_descripcion_producto")]
    ejecutor.migrate(antes)
    categoria_vieja = ejecutor.loader.project_state(antes).apps.get_model("catalogo", "Categoria")
    for nombre in ("Arroz", "Crema dental", "Leche", "Artículos varios"):
        categoria_vieja.objects.get_or_create(nombre=nombre)

    ejecutor = MigrationExecutor(connection)
    ejecutor.migrate(ejecutor.loader.graph.leaf_nodes())  # hasta la última
    esperado = {
        "Arroz": "mercado",
        "Crema dental": "salud_belleza",
        "Leche": "lacteos_huevos",
        "Artículos varios": "otros",
    }
    for nombre, grupo in esperado.items():
        assert Categoria.objects.get(nombre=nombre).grupo == grupo
