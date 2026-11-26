"""Departamentos amplios en la portada y en el listado (Mercado, Salud y belleza…)."""

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.catalogo.models import Categoria, Presentacion, Producto
from apps.comparacion.selectors import grupos_para_portada
from apps.precios import services

pytestmark = pytest.mark.django_db


@pytest.fixture
def surtido(reportante, tiendas):
    """Un producto con precio en cada departamento que se prueba."""
    creados = {}
    for nombre, categoria, grupo in [
        ("Arroz", "Arroz", "mercado"),
        ("Leche", "Leche", "lacteos_huevos"),
        ("Crema Ponds", "Cremas", "salud_belleza"),
        ("Detergente", "Detergente", "aseo_hogar"),
    ]:
        cat = Categoria.objects.create(nombre=categoria, grupo=grupo)
        prod = Producto.objects.create(
            nombre=nombre, nombre_normalizado=nombre.lower(), categoria=cat
        )
        pres = Presentacion.objects.create(producto=prod, cantidad=Decimal("1"), unidad="kg")
        services.registrar_reporte(
            autor=reportante, presentacion_id=pres.pk, establecimiento_id=tiendas[0].pk, precio=5000
        )
        creados[grupo] = prod
    return creados


def test_sin_precios_no_hay_departamentos_en_la_portada(client):
    html = client.get(reverse("comparacion:inicio")).content.decode()
    assert "cat-rapidas" not in html


def test_la_portada_muestra_departamentos_en_un_orden_fijo_y_solo_los_que_tienen_precios(
    client, surtido
):
    etiquetas = [g.etiqueta for g in grupos_para_portada()]
    assert etiquetas == ["Mercado", "Lácteos y huevos", "Aseo del hogar", "Salud y belleza"]
    html = client.get(reverse("comparacion:inicio")).content.decode()
    zona = html.split('class="chips hero-chips cat-rapidas"')[1].split("</nav>")[0]
    for etiqueta in etiquetas:
        assert etiqueta in zona
    assert zona.index("Mercado") < zona.index("Salud y belleza")  # el orden no es comercial
    assert "Bebidas" not in zona and "Más categorías" in zona


def test_cada_departamento_lleva_al_listado_filtrado(client, surtido):
    html = client.get(reverse("comparacion:inicio")).content.decode()
    assert "?grupo=salud_belleza" in html and "?grupo=mercado" in html


def test_un_departamento_sin_precios_publicados_no_aparece(client, surtido, db):
    cat = Categoria.objects.create(nombre="Gaseosas", grupo="bebidas")
    Producto.objects.create(nombre="Cola", nombre_normalizado="cola", categoria=cat)
    assert "Bebidas" not in [g.etiqueta for g in grupos_para_portada()]


def test_las_categorias_inactivas_no_cuentan(client, surtido):
    Categoria.objects.filter(grupo="salud_belleza").update(activa=False)
    assert "Salud y belleza" not in [g.etiqueta for g in grupos_para_portada()]


def test_el_listado_filtra_por_departamento(client, surtido):
    html = client.get(reverse("comparacion:productos"), {"grupo": "salud_belleza"}).content.decode()
    assert "Crema Ponds" in html and "Detergente" not in html and "Arroz" not in html


def test_un_departamento_desconocido_se_ignora_y_muestra_todo(client, surtido):
    html = client.get(reverse("comparacion:productos"), {"grupo": "inventado"}).content.decode()
    assert "Crema Ponds" in html and "Arroz" in html


def test_el_filtro_del_listado_ofrece_los_departamentos_y_marca_el_elegido(client, surtido):
    html = client.get(reverse("comparacion:productos"), {"grupo": "aseo_hogar"}).content.decode()
    assert 'name="grupo"' in html and 'value="aseo_hogar" selected' in html
    assert "Departamento" in html


def test_el_departamento_se_combina_con_la_categoria(client, surtido):
    cat = Categoria.objects.get(nombre="Cremas")
    html = client.get(
        reverse("comparacion:productos"), {"grupo": "salud_belleza", "categoria": cat.pk}
    ).content.decode()
    assert "Crema Ponds" in html


def test_el_listado_no_hace_consultas_de_mas(client, surtido, django_assert_max_num_queries):
    with django_assert_max_num_queries(22):
        client.get(reverse("comparacion:productos"), {"grupo": "mercado"})
