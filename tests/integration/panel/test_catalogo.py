"""CRUD del catálogo en el panel: marcas, categorías y productos con sus presentaciones."""

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.administracion.models import RegistroAuditoria
from apps.catalogo import selectors as catalogo
from apps.catalogo.models import Categoria, Marca, Presentacion, Producto
from apps.precios import services as precios

from .conftest import controles_sin_etiqueta, referencias_rotas

pytestmark = pytest.mark.integration


def _formset(prefijo="presentaciones", filas=(), iniciales=0, **extra):
    datos = {
        f"{prefijo}-TOTAL_FORMS": str(len(filas)),
        f"{prefijo}-INITIAL_FORMS": str(iniciales),
        f"{prefijo}-MIN_NUM_FORMS": "1",
        f"{prefijo}-MAX_NUM_FORMS": "1000",
    }
    for i, fila in enumerate(filas):
        datos.update({f"{prefijo}-{i}-{k}": v for k, v in fila.items()})
    datos.update(extra)
    return datos


# ---------- Marcas ----------


def test_crear_una_marca_queda_en_la_auditoria(entrar, db):
    client, admin = entrar("administrador")
    r = client.post(reverse("panel:nuevo", args=["marcas"]), {"nombre": "  Águila Roja "})
    assert r.status_code == 302
    marca = Marca.objects.get()
    assert marca.nombre == "Águila Roja" and marca.activa
    registro = RegistroAuditoria.objects.get()
    assert (registro.actor, registro.accion, registro.entidad) == (admin, "crear", "marca")
    assert registro.objeto_id == marca.pk and registro.creado_en is not None
    assert registro.cambios["nombre"] == [None, "Águila Roja"]


def test_una_marca_repetida_sin_tildes_se_rechaza(entrar, datos):
    client, _ = entrar("editor_catalogo")
    r = client.post(reverse("panel:nuevo", args=["marcas"]), {"nombre": "DIANA"})
    assert r.status_code == 200
    assert "Ya existe una marca" in r.content.decode()
    assert Marca.objects.count() == 1
    assert not RegistroAuditoria.objects.exists()


def test_editar_registra_solo_lo_que_cambio(entrar, datos):
    client, _ = entrar("editor_catalogo")
    client.post(
        reverse("panel:editar", args=["marcas", datos["diana"].pk]), {"nombre": "Diana S.A."}
    )
    registro = RegistroAuditoria.objects.get()
    assert registro.accion == "editar"
    assert registro.cambios == {"nombre": ["Diana", "Diana S.A."]}


def test_listado_con_busqueda_filtro_y_paginacion_de_20(entrar, db):
    for i in range(25):
        Marca.objects.create(nombre=f"Marca {i:02d}", activa=i % 5 != 0)
    client, _ = entrar("editor_catalogo")
    url = reverse("panel:lista", args=["marcas"])
    html = client.get(url).content.decode()
    assert html.count('class="fila-panel"') == 20
    assert "Página 1 de 2" in html
    assert client.get(url, {"pagina": 2}).content.decode().count('class="fila-panel"') == 5
    assert client.get(url, {"q": "marca 07"}).content.decode().count('class="fila-panel"') == 1
    inactivas = client.get(url, {"activa": "no"}).content.decode()
    assert inactivas.count('class="fila-panel"') == 5


def test_el_listado_responde_con_el_fragmento_por_htmx(entrar, datos):
    client, _ = entrar("editor_catalogo")
    url = reverse("panel:lista", args=["marcas"])
    completo = client.get(url).content.decode()
    assert 'id="resultados-panel" aria-live="polite"' in completo
    fragmento = client.get(url, {"q": "dia"}, HTTP_HX_REQUEST="true").content.decode()
    assert "<html" not in fragmento and "Diana" in fragmento


def test_desactivar_pide_confirmacion_y_la_marca_deja_de_ofrecerse(entrar, datos):
    client, _ = entrar("editor_catalogo")
    url = reverse("panel:estado", args=["marcas", datos["diana"].pk])
    confirmacion = client.get(url).content.decode()
    assert "¿Desactivar la marca «Diana»?" in confirmacion
    assert 'method="post"' in confirmacion
    datos["diana"].refresh_from_db()
    assert datos["diana"].activa  # el GET no cambia nada
    assert client.post(url).status_code == 302
    datos["diana"].refresh_from_db()
    assert not datos["diana"].activa
    assert "Diana" not in catalogo.opciones_de_filtro()["marcas"]
    registro = RegistroAuditoria.objects.get()
    assert registro.accion == "desactivar" and registro.cambios == {"activa": [True, False]}
    client.post(url)  # el mismo botón la reactiva
    datos["diana"].refresh_from_db()
    assert datos["diana"].activa


def test_una_marca_sin_productos_se_elimina_y_con_productos_no(entrar, datos):
    client, _ = entrar("editor_catalogo")
    sola = Marca.objects.create(nombre="Sin productos")
    assert client.post(reverse("panel:eliminar", args=["marcas", sola.pk])).status_code == 302
    assert not Marca.objects.filter(pk=sola.pk).exists()
    assert RegistroAuditoria.objects.get().accion == "eliminar"

    r = client.post(reverse("panel:eliminar", args=["marcas", datos["diana"].pk]), follow=True)
    assert Marca.objects.filter(pk=datos["diana"].pk).exists()
    assert "No se puede eliminar" in r.content.decode()
    assert RegistroAuditoria.objects.count() == 1  # el intento fallido no deja registro


# ---------- Categorías ----------


def test_categoria_se_crea_y_se_desactiva(entrar, db):
    client, _ = entrar("editor_catalogo")
    client.post(
        reverse("panel:nuevo", args=["categorias"]), {"nombre": "Frescos", "perecedera": "on"}
    )
    frescos = Categoria.objects.get(nombre="Frescos")
    assert frescos.perecedera
    client.post(reverse("panel:estado", args=["categorias", frescos.pk]))
    frescos.refresh_from_db()
    assert not frescos.activa


# ---------- Productos y presentaciones ----------


def test_el_formulario_de_producto_ofrece_las_cinco_unidades(entrar, datos):
    client, _ = entrar("editor_catalogo")
    html = client.get(reverse("panel:nuevo", args=["productos"])).content.decode()
    for unidad in ["g", "kg", "ml", "L", "und"]:
        assert f'<option value="{unidad}">' in html
    assert controles_sin_etiqueta(html) == []
    assert referencias_rotas(html) == []


def test_crear_producto_con_sus_presentaciones(entrar, datos):
    client, _ = entrar("editor_catalogo")
    filas = [
        {"cantidad": "1", "unidad": "L", "codigo_barras": "7702001001234", "activa": "on"},
        {"cantidad": "900", "unidad": "ml", "codigo_barras": "", "activa": "on"},
    ]
    datos_form = _formset(
        filas=filas, nombre="Leche entera", marca="", categoria=datos["granos"].pk
    )
    r = client.post(reverse("panel:nuevo", args=["productos"]), datos_form)
    assert r.status_code == 302, r.content.decode()[:500]
    leche = Producto.objects.get(nombre="Leche entera")
    assert leche.nombre_normalizado == "leche entera" and leche.marca is None
    assert {(str(p.cantidad.normalize()), p.unidad) for p in leche.presentaciones.all()} == {
        ("1", "L"),
        ("9E+2", "ml"),
    }
    registro = RegistroAuditoria.objects.get()
    assert registro.entidad == "producto" and "presentaciones" in registro.cambios


def test_codigo_de_barras_invalido_y_producto_repetido_se_rechazan(entrar, datos):
    client, _ = entrar("editor_catalogo")
    malo = _formset(
        filas=[{"cantidad": "1", "unidad": "kg", "codigo_barras": "12AB", "activa": "on"}],
        nombre="Lentejas",
        marca="",
        categoria=datos["granos"].pk,
    )
    html = client.post(reverse("panel:nuevo", args=["productos"]), malo).content.decode()
    assert "8 a 14 dígitos" in html
    repetido = _formset(
        filas=[{"cantidad": "1", "unidad": "kg", "codigo_barras": "", "activa": "on"}],
        nombre="ARROZ BLANCO",
        marca=datos["diana"].pk,
        categoria=datos["granos"].pk,
    )
    html = client.post(reverse("panel:nuevo", args=["productos"]), repetido).content.decode()
    assert "Ya existe ese producto con esa marca" in html
    assert Producto.objects.count() == 1


def test_una_presentacion_con_reportes_no_se_borra(entrar, datos, reportante):
    precios.registrar_reporte(
        autor=reportante,
        presentacion_id=datos["p500"].pk,
        establecimiento_id=datos["tienda"].pk,
        precio=Decimal(2600),
    )
    client, _ = entrar("editor_catalogo")
    fila = {
        "id": datos["p500"].pk,
        "cantidad": "500",
        "unidad": "g",
        "codigo_barras": "",
        "activa": "on",
        "DELETE": "on",
    }
    datos_form = _formset(
        filas=[fila],
        iniciales=1,
        nombre="Arroz blanco",
        marca=datos["diana"].pk,
        categoria=datos["granos"].pk,
    )
    r = client.post(reverse("panel:editar", args=["productos", datos["arroz"].pk]), datos_form)
    assert Presentacion.objects.filter(pk=datos["p500"].pk).exists()
    assert "tiene reportes" in r.content.decode()


def test_un_producto_con_reportes_no_se_elimina_pero_se_desactiva(entrar, datos, reportante):
    precios.registrar_reporte(
        autor=reportante,
        presentacion_id=datos["p500"].pk,
        establecimiento_id=datos["tienda"].pk,
        precio=Decimal(2600),
    )
    client, _ = entrar("editor_catalogo")
    url = reverse("panel:eliminar", args=["productos", datos["arroz"].pk])
    assert "Desactívalo" in client.get(url).content.decode()  # se avisa antes de intentar
    client.post(url)
    assert Producto.objects.filter(pk=datos["arroz"].pk).exists()
    client.post(reverse("panel:estado", args=["productos", datos["arroz"].pk]))
    datos["arroz"].refresh_from_db()
    assert not datos["arroz"].activo
    assert catalogo.buscar_productos("arroz").count() == 0


def test_un_producto_sin_reportes_se_elimina_con_sus_presentaciones(entrar, datos):
    client, _ = entrar("editor_catalogo")
    client.post(reverse("panel:eliminar", args=["productos", datos["arroz"].pk]))
    assert not Producto.objects.exists() and not Presentacion.objects.exists()


@pytest.mark.parametrize("seccion", ["marcas", "categorias", "productos", "establecimientos"])
def test_las_paginas_del_panel_son_accesibles(entrar, datos, seccion):
    client, _ = entrar("administrador")
    for url in [
        reverse("panel:lista", args=[seccion]),
        reverse("panel:nuevo", args=[seccion]),
    ]:
        html = client.get(url).content.decode()
        assert controles_sin_etiqueta(html) == [], url
        assert referencias_rotas(html) == [], url
        assert "<caption" in html or "nuevo" in url  # tablas con título (1.3.1)
