"""RF-19: filtros de la comparación por municipio y barrio. Solo reducen; el orden no cambia."""

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.comparacion.domain.ranking import CRITERIO_DECLARADO
from apps.comparacion.selectors import comparar_producto
from apps.establecimientos.models import Establecimiento
from apps.precios import services

pytestmark = pytest.mark.integration


@pytest.fixture
def con_precios(reportante, arroz, tiendas):
    producto, p500, _ = arroz
    rosa, super_ = tiendas  # ambos en Centro, Armenia
    calarca = Establecimiento.objects.create(
        nombre="Mini Calarcá",
        tipo="minimercado",
        direccion="Cra 25",
        barrio="Centro",
        municipio="Calarcá",
    )
    granada = Establecimiento.objects.create(
        nombre="Tienda Granada",
        tipo="tienda",
        direccion="Cra 19",
        barrio="Granada",
        municipio="Armenia",
    )
    for local, precio in [(rosa, 2600), (super_, 2400), (calarca, 2300), (granada, 2500)]:
        services.registrar_reporte(
            autor=reportante,
            presentacion_id=p500.pk,
            establecimiento_id=local.pk,
            precio=Decimal(precio),
        )
    return producto


def _nombres(html: str, candidatos) -> list[str]:
    return sorted((n for n in candidatos if n in html), key=html.index)


NOMBRES = ["Mini Calarcá", "Súper Quindío", "Tienda Granada", "Tienda Doña Rosa"]


def test_sin_filtros_muestra_todo_en_orden_neutral(client, con_precios):
    html = client.get(reverse("comparacion:comparar", args=[con_precios.pk])).content.decode()
    assert _nombres(html, NOMBRES) == NOMBRES  # menor precio por unidad primero
    assert CRITERIO_DECLARADO in html  # el criterio siempre visible
    assert '<label for="f-municipio">Municipio</label>' in html


def test_filtrar_por_municipio_y_barrio_solo_reduce(client, con_precios):
    url = reverse("comparacion:comparar", args=[con_precios.pk])
    html = client.get(url, {"municipio": "Armenia"}).content.decode()
    assert _nombres(html, NOMBRES) == ["Súper Quindío", "Tienda Granada", "Tienda Doña Rosa"]
    html = client.get(url, {"municipio": "armenia", "barrio": "CENTRO"}).content.decode()
    assert _nombres(html, NOMBRES) == ["Súper Quindío", "Tienda Doña Rosa"]
    assert "Los filtros solo ocultan resultados; no cambian el orden." in html


def test_filtro_por_htmx_devuelve_el_fragmento_con_el_criterio(client, con_precios):
    url = reverse("comparacion:comparar", args=[con_precios.pk])
    html = client.get(url, {"barrio": "Granada"}, HTTP_HX_REQUEST="true").content.decode()
    assert "<html" not in html
    assert _nombres(html, NOMBRES) == ["Tienda Granada"]
    assert CRITERIO_DECLARADO in html


def test_filtro_sin_coincidencias_lo_explica(client, con_precios):
    url = reverse("comparacion:comparar", args=[con_precios.pk])
    html = client.get(url, {"municipio": "Pereira"}).content.decode()
    assert "No hay precios vigentes con esos filtros" in html
    assert CRITERIO_DECLARADO in html


def test_la_api_publica_no_cambia(con_precios):
    resultados = comparar_producto(con_precios.pk)
    assert [r.establecimiento for r in resultados] == NOMBRES
    assert not hasattr(resultados[0], "reporte_id")  # el contrato público no expone reportes
