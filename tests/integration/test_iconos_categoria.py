"""Íconos por categoría en las pantallas donde ayudan a reconocer el producto (prototipo visual).

Son dibujos propios dentro del sprite SVG: ni una imagen ni una petición de red más (EC-01 en 3G).
Decorativos (aria-hidden): el nombre del producto sigue siendo el texto accesible (M-03).
"""

import re
from decimal import Decimal
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse

from apps.catalogo.domain.iconos import ICONO_GENERICO, ICONOS
from apps.catalogo.models import Categoria, Presentacion, Producto
from apps.precios import services

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

SPRITE = Path(settings.BASE_DIR) / "templates" / "partials" / "_iconos.html"
REGISTRAR = reverse("precios:registrar")


def _usa(html: str, icono: str) -> bool:
    return f'<use href="#{icono}"' in html


def test_el_sprite_dibuja_todos_los_iconos_de_categoria():
    sprite = SPRITE.read_text(encoding="utf-8")
    faltan = [i for i in sorted(ICONOS) if f'id="{i}"' not in sprite]
    assert faltan == []


def test_el_sprite_solo_usa_dibujos_propios_sin_imagenes_externas():
    sprite = SPRITE.read_text(encoding="utf-8")
    assert "http" not in sprite.replace('xmlns="http://www.w3.org/2000/svg"', "")
    assert "<image" not in sprite


def test_la_lista_de_registrar_muestra_el_icono_de_cada_producto(client, reportante, arroz):
    client.force_login(reportante)
    html = client.get(REGISTRAR).content.decode()
    assert _usa(html, "i-cat-grano")  # «Granos»
    principal = html[html.index('id="resultados-producto"') : html.index("</main>")]
    assert "<img" not in principal  # el botón flotante del asistente va fuera del contenido


def test_la_busqueda_en_vivo_tambien_trae_los_iconos(client, reportante, arroz):
    client.force_login(reportante)
    html = client.get(REGISTRAR, {"q": "arro"}, HTTP_HX_REQUEST="true").content.decode()
    assert _usa(html, "i-cat-grano")


def test_el_producto_elegido_muestra_su_icono(client, reportante, arroz, tiendas):
    client.force_login(reportante)
    html = client.get(REGISTRAR, {"producto": arroz[0].pk}).content.decode()
    caja = html[html.index("producto-elegido") : html.index("Cambiar producto")]
    assert _usa(caja, "i-cat-grano")


def test_la_comparacion_muestra_el_icono_del_producto(client, reportante, arroz, tiendas):
    prod, p500, _ = arroz
    services.registrar_reporte(
        autor=reportante,
        presentacion_id=p500.pk,
        establecimiento_id=tiendas[0].pk,
        precio=Decimal("2500"),
    )
    html = client.get(reverse("comparacion:comparar", args=[prod.pk])).content.decode()
    encabezado = html[html.index('class="encabezado') : html.index("<h1")]
    assert _usa(encabezado, "i-cat-grano")


def test_el_listado_de_productos_muestra_el_icono_de_cada_categoria(client, reportante, arroz):
    html = client.get(reverse("comparacion:productos")).content.decode()
    assert _usa(html, "i-cat-grano")


def test_una_categoria_desconocida_muestra_el_icono_generico(client, reportante, tiendas):
    cat = Categoria.objects.create(nombre="Ferretería")
    prod = Producto.objects.create(nombre="Martillo", nombre_normalizado="martillo", categoria=cat)
    Presentacion.objects.create(producto=prod, cantidad=Decimal("1"), unidad="und")
    client.force_login(reportante)
    html = client.get(REGISTRAR, {"producto": prod.pk}).content.decode()
    assert _usa(html, ICONO_GENERICO)


def test_los_iconos_son_decorativos_para_lectores_de_pantalla(client, reportante, arroz):
    client.force_login(reportante)
    html = client.get(REGISTRAR).content.decode()
    usos = re.findall(r'<svg[^>]*>(?:(?!</svg>).)*?<use href="#i-cat-[a-z]+"', html, flags=re.S)
    assert usos and all('aria-hidden="true"' in u for u in usos)
