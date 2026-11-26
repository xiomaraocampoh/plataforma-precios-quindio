"""Página de un establecimiento: qué precios vigentes tiene registrados (lado lectura).

No es un ranking: dentro de un comercio los productos van en orden alfabético. El orden neutral
(EC-06) sigue siendo el de la comparación de UN producto entre comercios.
"""

import re
from decimal import Decimal

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.catalogo.models import Presentacion, Producto
from apps.establecimientos.models import Establecimiento
from apps.precios import services

pytestmark = pytest.mark.integration


def _url(local) -> str:
    return reverse("comparacion:establecimiento", args=[local.pk])


@pytest.fixture
def con_precios(reportante, arroz, tiendas):
    """Súper Quindío: arroz 1 kg a $8.000. Tienda Doña Rosa: arroz 500 g a $4.500."""
    _, p500, p1kg = arroz
    rosa, super_ = tiendas
    services.registrar_reporte(
        autor=reportante, presentacion_id=p500.pk, establecimiento_id=rosa.pk, precio=4500
    )
    services.registrar_reporte(
        autor=reportante, presentacion_id=p1kg.pk, establecimiento_id=super_.pk, precio=8000
    )
    return tiendas


def _otro_producto(arroz, nombre, cantidad="1", unidad="L"):
    prod = Producto.objects.create(
        nombre=nombre, nombre_normalizado=nombre.lower(), categoria=arroz[0].categoria
    )
    return Presentacion.objects.create(producto=prod, cantidad=Decimal(cantidad), unidad=unidad)


def test_la_pagina_muestra_solo_los_precios_de_ese_comercio(client, con_precios):
    rosa, super_ = con_precios
    r = client.get(_url(super_))
    html = r.content.decode()
    assert r.status_code == 200
    assert "Súper Quindío" in html and "Arroz blanco" in html and "$8.000" in html
    assert "$4.500" not in html  # ese precio es de otro comercio


def test_cada_fila_lleva_a_comparar_ese_producto_en_otros_comercios(client, con_precios, arroz):
    _, super_ = con_precios
    html = client.get(_url(super_)).content.decode()
    assert reverse("comparacion:comparar", args=[arroz[0].pk]) in html


def test_los_productos_van_en_orden_alfabetico_y_sin_ranking(
    client, con_precios, arroz, reportante
):
    _, super_ = con_precios
    aceite = _otro_producto(arroz, "Aceite vegetal")
    services.registrar_reporte(
        autor=reportante, presentacion_id=aceite.pk, establecimiento_id=super_.pk, precio=12000
    )
    html = client.get(_url(super_)).content.decode()
    assert html.index("Aceite vegetal") < html.index("Arroz blanco")  # alfabético, no por precio
    assert "Primero en el orden" not in html and "Más barato" not in html


def test_un_comercio_sin_precios_lo_explica_y_invita_a_registrar(client, tiendas):
    rosa, _ = tiendas
    html = client.get(_url(rosa)).content.decode()
    assert "Aún no hay precios vigentes" in html
    assert reverse("precios:registrar") in html


def test_un_comercio_pendiente_o_inactivo_no_existe_para_el_publico(client, tiendas):
    rosa, super_ = tiendas
    Establecimiento.objects.filter(pk=rosa.pk).update(
        estado=Establecimiento.Estado.PENDIENTE,
        activo=False,  # la BD exige pendiente ⇒ inactivo
    )
    Establecimiento.objects.filter(pk=super_.pk).update(activo=False)
    assert client.get(_url(rosa)).status_code == 404
    assert client.get(_url(super_)).status_code == 404


def test_la_pagina_no_expone_al_autor(client, con_precios, reportante):  # M-15
    _, super_ = con_precios
    html = client.get(_url(super_)).content.decode()
    assert reportante.username not in html


def test_el_directorio_enlaza_a_la_pagina_de_cada_comercio(client, con_precios):
    rosa, super_ = con_precios
    html = client.get(reverse("establecimientos:directorio")).content.decode()
    assert _url(rosa) in html and _url(super_) in html


def test_el_numero_de_consultas_no_crece_con_los_productos(client, con_precios, arroz, reportante):
    _, super_ = con_precios
    client.get(_url(super_))  # calienta
    with CaptureQueriesContext(connection) as pocas:
        client.get(_url(super_))
    for i in range(4):
        pres = _otro_producto(arroz, f"Producto {i}")
        services.registrar_reporte(
            autor=reportante, presentacion_id=pres.pk, establecimiento_id=super_.pk, precio=1000
        )
    with CaptureQueriesContext(connection) as muchas:
        html = client.get(_url(super_)).content.decode()
    assert len(re.findall(r"Producto \d", html)) >= 4
    assert len(muchas) == len(pocas)  # sin N+1


def test_la_pagina_usa_las_tarjetas_tipo_catalogo_con_foto(client, con_precios, arroz, imagen):
    from apps.catalogo import services as catalogo

    _, super_ = con_precios
    catalogo.guardar_foto(arroz[0], catalogo.preparar_foto(imagen()))
    html = client.get(_url(super_)).content.decode()
    assert 'class="tarjetas tarjetas-precio"' in html  # la misma cuadrícula del listado
    assert reverse("catalogo:foto", args=[arroz[0].pk]) in html  # foto del producto
    assert 'class="tp-comercio"' not in html  # el comercio ya está en el encabezado
    assert "Registrar precio aquí" in html  # un toque, con comercio y presentación elegidos


def test_toda_la_tarjeta_del_directorio_es_clicable_con_un_solo_enlace(client, con_precios):
    rosa, _ = con_precios
    html = client.get(reverse("establecimientos:directorio")).content.decode()
    assert "tarjeta-enlace" in html  # el enlace del nombre se extiende a toda la tarjeta
    assert (
        html.count(f'href="{_url(rosa)}"') == 1
    )  # un solo enlace por comercio (lector de pantalla)
