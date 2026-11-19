"""Catálogo con fotos: la foto del producto en las pantallas donde se elige y se compara (EC-01, M-03).

Sin foto se ve el ícono de la categoría (respaldo). La imagen es decorativa (alt vacío): el nombre del
producto sigue siendo el texto accesible. Listar con fotos no hace consultas extra ni trae los bytes.
"""

import re
from decimal import Decimal

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.catalogo import services
from apps.catalogo.models import Categoria, Presentacion, Producto
from apps.precios import services as precios

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

REGISTRAR = reverse("precios:registrar")


@pytest.fixture
def arroz_con_foto(arroz, imagen):
    prod, _, _ = arroz
    services.guardar_foto(prod, services.preparar_foto(imagen()))
    prod.refresh_from_db()
    return prod


def _img(prod) -> str:
    return f'src="{reverse("catalogo:foto", args=[prod.pk])}?v={prod.foto_version}"'


def _reportar(reportante, presentacion, tienda):
    precios.registrar_reporte(
        autor=reportante,
        presentacion_id=presentacion.pk,
        establecimiento_id=tienda.pk,
        precio=Decimal("2500"),
    )


def test_la_lista_de_registrar_muestra_la_foto_de_cada_producto(client, reportante, arroz_con_foto):
    client.force_login(reportante)
    html = client.get(REGISTRAR).content.decode()
    assert _img(arroz_con_foto) in html


def test_la_imagen_es_decorativa_perezosa_y_de_tamano_fijo(client, reportante, arroz_con_foto):
    client.force_login(reportante)
    html = client.get(REGISTRAR).content.decode()
    etiqueta = re.search(r"<img[^>]*catalogo/productos[^>]*>", html).group(0)
    assert 'alt=""' in etiqueta  # el nombre ya está en el texto: no se lee dos veces
    assert 'loading="lazy"' in etiqueta and 'decoding="async"' in etiqueta
    assert 'width="480"' in etiqueta and 'height="480"' in etiqueta  # sin saltos de diseño (CLS)


def test_sin_foto_se_muestra_el_icono_de_la_categoria_y_ninguna_imagen(client, reportante, arroz):
    client.force_login(reportante)
    html = client.get(REGISTRAR).content.decode()
    assert '<use href="#i-cat-grano"' in html and "catalogo/productos/" not in html


def test_el_producto_elegido_muestra_su_foto(client, reportante, arroz_con_foto, tiendas):
    client.force_login(reportante)
    html = client.get(REGISTRAR, {"producto": arroz_con_foto.pk}).content.decode()
    caja = html[html.index("producto-elegido") : html.index("Cambiar producto")]
    assert _img(arroz_con_foto) in caja


def test_la_busqueda_en_vivo_trae_las_fotos(client, reportante, arroz_con_foto):
    client.force_login(reportante)
    html = client.get(REGISTRAR, {"q": "arro"}, HTTP_HX_REQUEST="true").content.decode()
    assert _img(arroz_con_foto) in html


def test_la_comparacion_muestra_la_foto_del_producto(
    client, reportante, arroz_con_foto, arroz, tiendas
):
    _reportar(reportante, arroz[1], tiendas[0])
    html = client.get(reverse("comparacion:comparar", args=[arroz_con_foto.pk])).content.decode()
    encabezado = html[html.index('class="encabezado') : html.index("<h1")]
    assert _img(arroz_con_foto) in encabezado


def test_el_listado_de_productos_muestra_las_fotos(client, arroz_con_foto):
    html = client.get(reverse("comparacion:productos")).content.decode()
    assert _img(arroz_con_foto) in html


def test_la_portada_muestra_las_fotos_de_los_productos_destacados(
    client, reportante, arroz_con_foto, arroz, tiendas
):
    _reportar(reportante, arroz[1], tiendas[0])
    html = client.get(reverse("comparacion:inicio")).content.decode()
    assert _img(arroz_con_foto) in html


# ───────────── Rendimiento: las fotos no cuestan consultas ─────────────


def _crear_productos(n: int, imagen, desde: int = 0):
    cat, _ = Categoria.objects.get_or_create(nombre="Lácteos")
    miniatura = services.preparar_foto(imagen())
    for i in range(desde, desde + n):
        prod = Producto.objects.create(nombre=f"Leche tipo {i}", categoria=cat)
        Presentacion.objects.create(producto=prod, cantidad=Decimal("1"), unidad="L")
        services.guardar_foto(prod, miniatura)


def _consultas(client, url, **params):
    with CaptureQueriesContext(connection) as capturadas:
        client.get(url, params)
    return [c["sql"] for c in capturadas.captured_queries]


@pytest.mark.parametrize("ruta", ["comparacion:productos", "comparacion:inicio"])
def test_listar_con_fotos_usa_un_numero_constante_de_consultas(client, imagen, ruta):
    _crear_productos(2, imagen)
    pocas = _consultas(client, reverse(ruta))
    _crear_productos(8, imagen, desde=2)
    muchas = _consultas(client, reverse(ruta))
    assert len(muchas) == len(pocas)  # sin N+1 por foto


def test_la_lista_de_registrar_tampoco_hace_una_consulta_por_foto(client, reportante, imagen):
    client.force_login(reportante)
    _crear_productos(2, imagen)
    pocas = _consultas(client, REGISTRAR)
    _crear_productos(8, imagen, desde=2)
    assert len(_consultas(client, REGISTRAR)) == len(pocas)


def test_ningun_listado_trae_los_bytes_de_las_fotos(client, reportante, imagen):
    client.force_login(reportante)
    _crear_productos(3, imagen)
    sqls = [
        *_consultas(client, reverse("comparacion:productos")),
        *_consultas(client, reverse("comparacion:inicio")),
        *_consultas(client, REGISTRAR),
        *_consultas(client, REGISTRAR, q="leche"),
    ]
    assert sqls and not [s for s in sqls if "catalogo_fotoproducto" in s and '"contenido"' in s]
