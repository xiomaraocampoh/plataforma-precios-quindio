"""Filtro por rango de precio en la comparación. Solo reduce; el orden no cambia (EC-06)."""

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.establecimientos.models import Establecimiento
from apps.precios import services

pytestmark = pytest.mark.integration

# Precio total de arroz de 500 g: Calarcá 2300 < Súper 2400 < Granada 2500 < Rosa 2600
EN_ORDEN = ["Mini Calarcá", "Súper Quindío", "Tienda Granada", "Tienda Doña Rosa"]


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


def _ver(client, producto, **filtros) -> str:
    url = reverse("comparacion:comparar", args=[producto.pk])
    respuesta = client.get(url, filtros)
    assert respuesta.status_code == 200
    return respuesta.content.decode()


def _nombres(html: str) -> list[str]:
    return sorted((n for n in EN_ORDEN if n in html), key=html.index)


def test_un_rango_muestra_solo_lo_que_cae_dentro_y_en_el_mismo_orden(client, con_precios):
    html = _ver(client, con_precios, precio_min="2400", precio_max="2500")
    assert _nombres(html) == ["Súper Quindío", "Tienda Granada"]


def test_solo_el_minimo_con_formato_colombiano(client, con_precios):
    html = _ver(client, con_precios, precio_min="2.500")  # 2.500 = dos mil quinientos
    assert _nombres(html) == ["Tienda Granada", "Tienda Doña Rosa"]


def test_solo_el_maximo_con_signo_de_pesos(client, con_precios):
    html = _ver(client, con_precios, precio_max="$2.400")
    assert _nombres(html) == ["Mini Calarcá", "Súper Quindío"]


def test_un_monto_ilegible_avisa_y_no_filtra(client, con_precios):
    html = _ver(client, con_precios, precio_min="abc")
    assert "No se aplicó el filtro de precio" in html
    assert _nombres(html) == EN_ORDEN  # se ven todos


def test_minimo_mayor_que_maximo_avisa_y_no_filtra(client, con_precios):
    html = _ver(client, con_precios, precio_min="3000", precio_max="2000")
    assert "No se aplicó el filtro de precio" in html
    assert _nombres(html) == EN_ORDEN


def test_un_rango_sin_coincidencias_lo_dice(client, con_precios):
    html = _ver(client, con_precios, precio_min="9000")
    assert "No hay precios vigentes con esos filtros" in html
    assert _nombres(html) == []


def test_se_combina_con_el_filtro_de_municipio(client, con_precios):
    html = _ver(client, con_precios, municipio="Armenia", precio_max="2400")
    assert _nombres(html) == ["Súper Quindío"]  # Calarcá cuesta 2300 pero no es de Armenia


def test_el_fragmento_htmx_respeta_el_filtro(client, con_precios):
    url = reverse("comparacion:comparar", args=[con_precios.pk])
    html = client.get(url, {"precio_max": "2300"}, HTTP_HX_REQUEST="true").content.decode()
    assert _nombres(html) == ["Mini Calarcá"]
    assert "<html" not in html  # es solo el fragmento


def test_el_formulario_tiene_etiquetas_y_conserva_lo_escrito(client, con_precios):
    html = _ver(client, con_precios, precio_min="2.400")
    assert '<label for="f-precio-min">Precio desde ($)</label>' in html
    assert '<label for="f-precio-max">Precio hasta ($)</label>' in html
    assert 'value="2.400"' in html


def test_el_formulario_aparece_aunque_todos_esten_en_el_mismo_barrio(
    client, reportante, arroz, tiendas
):
    producto, p500, _ = arroz
    for local, precio in zip(tiendas, (2600, 2400), strict=True):
        services.registrar_reporte(
            autor=reportante,
            presentacion_id=p500.pk,
            establecimiento_id=local.pk,
            precio=Decimal(precio),
        )
    assert 'id="f-precio-min"' in _ver(client, producto)
