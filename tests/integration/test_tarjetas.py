"""Tarjetas de precio completas (RF-16) en la comparación, el listado y la API pública."""

import re
from decimal import Decimal

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.catalogo.models import Categoria, Marca, Presentacion, Producto
from apps.precios import services

pytestmark = pytest.mark.integration


@pytest.fixture
def con_precios(reportante, arroz, tiendas):
    """500 g a $4.500 ($9.000/kg) en la tienda y 1 kg a $8.000 en el súper."""
    prod, p500, p1kg = arroz
    prod.marca = Marca.objects.create(nombre="Diana")
    prod.save()
    rosa, super_ = tiendas
    services.registrar_reporte(
        autor=reportante, presentacion_id=p500.pk, establecimiento_id=rosa.pk, precio=4500
    )
    services.registrar_reporte(
        autor=reportante, presentacion_id=p1kg.pk, establecimiento_id=super_.pk, precio=8000
    )
    return prod


@pytest.fixture
def vecina(django_user_model):
    return django_user_model.objects.create_user(
        username="vecina", password=None, acepto_tratamiento_datos=True
    )


def _comparar(client, producto) -> str:
    return client.get(reverse("comparacion:comparar", args=[producto.pk])).content.decode()


def _tarjetas(html: str) -> list[str]:
    """Cada tarjeta, desde su <li class="tile …"> hasta el siguiente tile."""
    trozos = re.split(r'(?=<li class="tile )', html)
    return [t for t in trozos if t.startswith('<li class="tile tarjeta-precio')]


def _en_orden(texto: str, partes: list[str]) -> bool:
    posiciones = [texto.find(p) for p in partes]
    return -1 not in posiciones and posiciones == sorted(posiciones)


def test_la_tarjeta_muestra_todo_en_el_orden_pedido(client, con_precios, vecina):
    client.force_login(vecina)
    primera = _tarjetas(_comparar(client, con_precios))[0]  # 1 kg: $8.000/kg es el menor
    assert _en_orden(
        primera,
        [
            "1 kg",  # presentación (el producto y la marca van una sola vez, en la ficha)
            "$8.000",  # precio total
            "$8.000 por kg",  # precio por unidad con su unidad
            "Súper Quindío",  # comercio
            "Supermercado",  # tipo
            "Cra 14 # 10-20, Centro, Armenia",  # dirección, barrio y municipio
            "Ver en el mapa",
            "Reportado por usuarios",  # fuente
            "hace un momento",  # antigüedad
            "Confianza media",  # confianza con texto, no solo color
            "Sigue igual",
            "Denunciar",
        ],
    ), primera


def test_el_orden_sigue_siendo_neutral_por_precio_por_unidad(client, con_precios):  # M-06
    tarjetas = _tarjetas(_comparar(client, con_precios))
    assert "Súper Quindío" in tarjetas[0] and "$8.000 por kg" in tarjetas[0]
    assert "Tienda Doña Rosa" in tarjetas[1] and "$9.000 por kg" in tarjetas[1]


def test_el_mapa_usa_coordenadas_o_la_direccion(client, con_precios):
    html = _comparar(client, con_precios)
    assert "https://www.openstreetmap.org/?mlat=4.533889" in html
    assert "(se abre en otra pestaña)" in html
    assert 'rel="noopener noreferrer"' in html


def test_sin_cuenta_se_invita_a_ingresar_para_las_acciones(client, con_precios):
    html = _comparar(client, con_precios)
    assert "Ingresa para confirmar o denunciar" in html
    assert "Sigue igual" not in html


def test_quien_reporto_ve_que_es_suyo_y_no_puede_confirmarse(client, con_precios, reportante):
    client.force_login(reportante)
    html = _comparar(client, con_precios)
    assert "Este precio lo reportaste tú." in html
    assert ">Sigue igual<" not in html


def test_ninguna_tarjeta_expone_al_autor(client, con_precios, reportante, vecina):  # M-15
    client.force_login(vecina)
    for url in (
        reverse("comparacion:comparar", args=[con_precios.pk]),
        reverse("comparacion:productos"),
    ):
        html = client.get(url).content.decode()
        assert reportante.username not in html


def test_api_publica_devuelve_la_direccion_del_comercio_y_nada_del_autor(
    api, con_precios, reportante
):  # EC-07, M-15
    datos = api.get(reverse("api-comparacion", args=[con_precios.pk])).json()
    primero = datos["resultados"][0]
    assert set(primero) == {
        "establecimiento_id",
        "establecimiento",
        "establecimiento_tipo",
        "direccion",
        "barrio",
        "municipio",
        "presentacion",
        "precio",
        "precio_unitario",
        "unidad_base",
        "fuente",
        "confianza",
        "fecha_observacion",
        "es_promocion",
    }
    assert primero["direccion"] == "Cra 14 # 10-20" and primero["municipio"] == "Armenia"
    assert primero["establecimiento_tipo"] == "Supermercado"
    assert reportante.username not in str(datos)


def test_listado_muestra_la_primera_tarjeta_de_cada_producto(client, con_precios, arroz):
    sin_precio = Producto.objects.create(nombre="Lentejas", categoria=arroz[0].categoria)
    Presentacion.objects.create(producto=sin_precio, cantidad=Decimal("500"), unidad="g")
    html = client.get(reverse("comparacion:productos")).content.decode()
    assert "$8.000 por kg" in html and "Súper Quindío" in html  # primera en el orden neutral
    assert "Tienda Doña Rosa" not in html  # el listado solo muestra la primera
    assert "Aún no hay precios vigentes." in html
    assert "Ver todos los precios" in html and "Ver el producto" in html


def test_listado_sin_n_mas_1(client, reportante, tiendas):
    categoria = Categoria.objects.create(nombre="Granos")

    def crear(n: int) -> None:
        for i in range(n):
            producto = Producto.objects.create(nombre=f"Producto {n}-{i}", categoria=categoria)
            p = Presentacion.objects.create(producto=producto, cantidad=Decimal("1"), unidad="kg")
            services.cargar_reporte_historico(
                autor=reportante,
                presentacion_id=p.pk,
                establecimiento_id=tiendas[0].pk,
                precio=Decimal(1000 + i),
                fecha_observacion=p.producto.creado_en,
            )

    def consultas() -> int:
        from django.core.cache import cache

        cache.clear()
        with CaptureQueriesContext(connection) as capturadas:
            assert client.get(reverse("comparacion:productos")).status_code == 200
        return len(capturadas)

    crear(2)
    con_dos = consultas()
    crear(10)
    assert consultas() == con_dos  # número constante de queries


# ---------- registro de precio ----------


def test_registro_habla_de_precio_total_y_calcula_por_unidad(client, reportante, arroz, tiendas):
    client.force_login(reportante)
    html = client.get(reverse("precios:registrar"), {"producto": arroz[0].pk}).content.decode()
    assert "Precio total del empaque ($)" in html
    assert "El precio que marca la etiqueta para esa presentación" in html
    assert 'aria-describedby="id_precio_helptext"' in html
    assert "data-equivale" in html and 'aria-live="polite"' in html
    assert 'data-cantidad="500"' in html and 'data-unidad="g"' in html
    assert "js/precio-unidad.js" in html
    assert "góndola" not in html


@pytest.mark.parametrize("ruta", ["comparacion:inicio", "cuentas:registro"])
def test_los_textos_ya_no_hablan_de_gondola(client, db, ruta):
    html = client.get(reverse(ruta)).content.decode()
    assert "góndola" not in html
    assert "precio total del empaque" in html and "precio por unidad de medida" in html


# ---------- accesibilidad en el HTML del servidor (M-03, WCAG 2.2 AA) ----------


def _referencias_rotas(html: str) -> list[str]:
    ids = set(re.findall(r'\bid="([^"]+)"', html))
    citados = re.findall(r'aria-(?:describedby|labelledby|controls)="([^"]+)"', html)
    return sorted({ref for grupo in citados for ref in grupo.split()} - ids)


def _niveles(html: str) -> list[int]:
    return [int(n) for n in re.findall(r"<h([1-6])\b", html)]


def _chips_de_confianza(html: str, nivel: str) -> list[str]:
    return re.findall(rf'<li class="chip tp-confianza-{nivel}[^"]*">(.*?)</li>', html, re.S)


@pytest.mark.parametrize("con_sesion", [False, True])
def test_tarjetas_accesibles(client, con_precios, vecina, con_sesion):  # M-03
    if con_sesion:
        client.force_login(vecina)
    for url in (
        reverse("comparacion:comparar", args=[con_precios.pk]),
        reverse("comparacion:productos"),
    ):
        html = client.get(url).content.decode()
        assert _referencias_rotas(html) == []  # 1.3.1: cada tarjeta nombrada por su h2
        niveles = _niveles(html)
        assert niveles[0] == 1
        assert all(b - a <= 1 for a, b in zip(niveles, niveles[1:], strict=False))  # 1.3.1
        for enlace in re.findall(r'<a [^>]*target="_blank"[^>]*>.*?</a>', html, re.S):
            assert "se abre en otra pestaña" in enlace  # 3.2.5
        chips = _chips_de_confianza(html, "media")
        assert chips and all("Confianza media" in c for c in chips)  # 1.4.1: no solo color


def test_el_fragmento_htmx_de_resultados_tambien_es_accesible(client, con_precios, vecina):
    client.force_login(vecina)
    html = client.get(
        reverse("comparacion:comparar", args=[con_precios.pk]), HTTP_HX_REQUEST="true"
    ).content.decode()
    assert "<html" not in html and "tarjeta-precio" in html
    assert set(_referencias_rotas(html)) <= {"ayuda-sigue-igual"}  # vive en la página completa
