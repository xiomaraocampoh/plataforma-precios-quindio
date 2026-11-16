"""API v1 del catálogo: GET catalogo/productos/?q= y catalogo/productos/{id}/ (públicos)."""

import pytest
from django.urls import reverse

from apps.catalogo.models import Presentacion

pytestmark = pytest.mark.integration


def test_lista_productos_con_busqueda_normalizada(api, arroz):
    producto, _, _ = arroz
    r = api.get(reverse("api-productos"), {"q": "ARROZ"})
    assert r.status_code == 200
    datos = r.json()
    assert datos["count"] == 1
    item = datos["results"][0]
    assert item["id"] == producto.pk
    assert set(item) == {"id", "nombre", "marca", "categoria", "presentaciones"}  # lista blanca
    assert {p["descripcion"] for p in item["presentaciones"]} == {
        "Arroz blanco 500 g",
        "Arroz blanco 1 kg",
    }


def test_detalle_de_producto_y_404(api, arroz):
    producto, p500, _ = arroz
    Presentacion.objects.filter(pk=p500.pk).update(codigo_barras="7702001001234")
    r = api.get(reverse("api-producto", args=[producto.pk]))
    assert r.status_code == 200
    assert {p["codigo_barras"] for p in r.json()["presentaciones"]} == {"7702001001234", ""}
    assert api.get(reverse("api-producto", args=[99999])).status_code == 404


def test_busca_por_codigo_de_barras(api, arroz):
    _, p500, _ = arroz
    Presentacion.objects.filter(pk=p500.pk).update(codigo_barras="7702001001234")
    assert api.get(reverse("api-productos"), {"q": "7702001001234"}).json()["count"] == 1
