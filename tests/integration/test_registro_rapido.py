"""Registrar un precio con pocos toques (EC-01, M-01, M-04): del producto a «Guardar», sin listas.

PUX-01 mostró que nadie registró en ≤ 15 s: el selector con todas las presentaciones y la tienda
por elegir cada vez fueron las dificultades. El flujo ahora parte del producto, solo ofrece sus
presentaciones, recuerda la última tienda y se precarga desde la comparación.
"""

import re
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.catalogo.models import Categoria, Presentacion, Producto
from apps.precios import selectors, services
from apps.precios.models import ReportePrecio

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

URL = reverse("precios:registrar")


@pytest.fixture
def leche(db):
    cat = Categoria.objects.create(nombre="Lácteos")
    prod = Producto.objects.create(
        nombre="Leche entera", nombre_normalizado="leche entera", categoria=cat
    )
    return prod, Presentacion.objects.create(producto=prod, cantidad=Decimal("1"), unidad="L")


def _registrar(usuario, presentacion, tienda, precio="4500"):
    return services.registrar_reporte(
        autor=usuario,
        presentacion_id=presentacion.pk,
        establecimiento_id=tienda.pk,
        precio=Decimal(precio),
    )


def _pagina(client, **params):
    return client.get(URL, params).content.decode()


# ───────────── Selectores ─────────────


def test_la_ultima_tienda_es_la_del_ultimo_reporte_de_la_persona(reportante, arroz, tiendas):
    _, p500, p1kg = arroz
    _registrar(reportante, p500, tiendas[0])
    _registrar(reportante, p1kg, tiendas[1])
    assert selectors.ultimo_establecimiento_id(reportante) == tiendas[1].pk


def test_sin_reportes_no_hay_ultima_tienda(reportante):
    assert selectors.ultimo_establecimiento_id(reportante) is None


def test_la_ultima_tienda_ignora_los_locales_desactivados(reportante, arroz, tiendas):
    _, p500, p1kg = arroz
    _registrar(reportante, p500, tiendas[0])
    _registrar(reportante, p1kg, tiendas[1])
    tiendas[1].activo = False
    tiendas[1].save()
    assert selectors.ultimo_establecimiento_id(reportante) == tiendas[0].pk


def test_la_ultima_tienda_es_solo_de_quien_registra(reportante, django_user_model, arroz, tiendas):
    _, p500, _ = arroz
    otra = django_user_model.objects.create_user(username="otra", password="clave-segura-123")
    _registrar(otra, p500, tiendas[1])
    assert selectors.ultimo_establecimiento_id(reportante) is None  # M-15: nada ajeno


def test_los_productos_frecuentes_van_primero_los_mas_reportados(reportante, arroz, leche, tiendas):
    prod_arroz, p500, _ = arroz
    prod_leche, pl = leche
    _registrar(reportante, pl, tiendas[0])
    _registrar(reportante, p500, tiendas[0], "3000")
    _registrar(reportante, p500, tiendas[1], "3100")
    nombres = [p.nombre for p in selectors.productos_para_registrar()]
    assert nombres[:2] == ["Arroz blanco", "Leche entera"]


def test_sin_reportes_igual_se_ofrecen_productos_en_orden_alfabetico(arroz, leche):
    nombres = [p.nombre for p in selectors.productos_para_registrar()]
    assert nombres == ["Arroz blanco", "Leche entera"]


# ───────────── Paso 1: elegir el producto ─────────────


def test_sin_producto_la_pagina_pide_elegir_uno_y_no_muestra_listas_largas(
    client, reportante, arroz, leche
):
    client.force_login(reportante)
    html = _pagina(client)
    assert "¿Qué producto?" in html
    assert 'name="q"' in html  # búsqueda
    assert "<select" not in html  # nada de selectores con todo el catálogo
    assert f"?producto={arroz[0].pk}" in html  # productos a un toque
    assert 'name="precio"' not in html  # el formulario aparece al elegir


def test_la_busqueda_de_producto_filtra_y_enlaza_cada_resultado(client, reportante, arroz, leche):
    client.force_login(reportante)
    html = _pagina(client, q="arro")
    assert "Arroz blanco" in html
    assert "Leche entera" not in html
    assert f"?producto={arroz[0].pk}" in html


def test_la_busqueda_por_htmx_devuelve_solo_el_fragmento(client, reportante, arroz):
    client.force_login(reportante)
    r = client.get(URL, {"q": "arro"}, HTTP_HX_REQUEST="true")
    html = r.content.decode()
    assert "Arroz blanco" in html
    assert "<html" not in html


def test_una_busqueda_sin_resultados_lo_dice_y_ofrece_pedir_el_producto(client, reportante, arroz):
    client.force_login(reportante)
    html = _pagina(client, q="zzzzzz")
    assert "No encontramos" in html
    assert reverse("catalogo:solicitar") in html


# ───────────── Paso 2: el formulario del producto ─────────────


def test_con_producto_solo_se_ofrecen_sus_presentaciones_como_botones(
    client, reportante, arroz, leche, tiendas
):
    prod, p500, p1kg = arroz
    client.force_login(reportante)
    html = _pagina(client, producto=prod.pk)
    assert "Arroz blanco" in html
    assert 'type="radio"' in html
    assert f'value="{p500.pk}"' in html and f'value="{p1kg.pk}"' in html
    assert f'value="{leche[1].pk}"' not in html  # nada de otros productos
    assert 'name="precio"' in html


def test_con_una_sola_presentacion_ya_viene_elegida(client, reportante, leche, tiendas):
    prod, pl = leche
    client.force_login(reportante)
    html = _pagina(client, producto=prod.pk)
    assert re.search(rf'value="{pl.pk}"[^>]*checked', html)


def test_con_varias_presentaciones_ninguna_viene_elegida_a_menos_que_se_indique(
    client, reportante, arroz, tiendas
):
    prod, p500, p1kg = arroz
    client.force_login(reportante)
    assert "checked" not in _pagina(client, producto=prod.pk).split('name="presentacion"')[1][:600]
    html = _pagina(client, presentacion=p1kg.pk)
    assert re.search(rf'value="{p1kg.pk}"[^>]*checked', html)
    assert not re.search(rf'value="{p500.pk}"[^>]*checked', html)


def test_la_presentacion_indicada_deduce_el_producto(client, reportante, arroz, tiendas):
    _, p500, _ = arroz
    client.force_login(reportante)
    assert "Arroz blanco" in _pagina(client, presentacion=p500.pk)


def test_la_tienda_indicada_viene_elegida(client, reportante, arroz, tiendas):
    prod, _, _ = arroz
    client.force_login(reportante)
    html = _pagina(client, producto=prod.pk, establecimiento=tiendas[1].pk)
    assert re.search(rf'<option value="{tiendas[1].pk}" selected', html)


def test_sin_tienda_indicada_viene_la_ultima_que_uso_la_persona(client, reportante, arroz, tiendas):
    prod, p500, _ = arroz
    _registrar(reportante, p500, tiendas[1])
    client.force_login(reportante)
    html = _pagina(client, producto=prod.pk)
    assert re.search(rf'<option value="{tiendas[1].pk}" selected', html)


def test_un_producto_inexistente_o_retirado_vuelve_al_paso_uno(client, reportante, arroz):
    client.force_login(reportante)
    assert "¿Qué producto?" in _pagina(client, producto=999999)
    assert "¿Qué producto?" in _pagina(client, producto="abc")
    arroz[0].activo = False
    arroz[0].save()
    assert "¿Qué producto?" in _pagina(client, producto=arroz[0].pk)


def test_el_formulario_permite_cambiar_de_producto_y_va_al_primer_campo_pendiente(
    client, reportante, arroz, tiendas
):
    prod, p500, _ = arroz
    client.force_login(reportante)
    html = _pagina(client, presentacion=p500.pk, establecimiento=tiendas[0].pk)
    assert "Cambiar producto" in html
    assert 'name="precio"' in html and "autofocus" in html  # todo precargado: a escribir el precio


def test_guardar_con_lo_precargado_registra_el_precio(client, reportante, arroz, tiendas):
    prod, p500, _ = arroz
    client.force_login(reportante)
    respuesta = client.post(
        f"{URL}?producto={prod.pk}",
        {"establecimiento": tiendas[0].pk, "presentacion": p500.pk, "precio": "2500"},
        HTTP_HX_REQUEST="true",
    )
    assert ReportePrecio.objects.get().precio == Decimal("2500")
    assert "ya está publicado" in respuesta.content.decode()


def test_un_error_al_guardar_conserva_el_producto_y_sus_botones(client, reportante, arroz, tiendas):
    prod, p500, p1kg = arroz
    client.force_login(reportante)
    html = client.post(
        f"{URL}?producto={prod.pk}",
        {"establecimiento": tiendas[0].pk, "presentacion": p500.pk, "precio": "0"},
        HTTP_HX_REQUEST="true",
    ).content.decode()
    assert "error" in html
    assert f'value="{p1kg.pk}"' in html  # sigue pudiendo cambiar de presentación
    assert ReportePrecio.objects.count() == 0


def test_la_confirmacion_ofrece_registrar_otro_en_la_misma_tienda_y_ver_la_comparacion(
    client, reportante, arroz, tiendas
):
    prod, p500, _ = arroz
    client.force_login(reportante)
    html = client.post(
        f"{URL}?producto={prod.pk}",
        {"establecimiento": tiendas[0].pk, "presentacion": p500.pk, "precio": "2500"},
        HTTP_HX_REQUEST="true",
    ).content.decode()
    assert f"establecimiento={tiendas[0].pk}" in html  # «Registrar otro aquí»
    assert reverse("comparacion:comparar", args=[prod.pk]) in html


def test_el_registro_sigue_exigiendo_cuenta(client, arroz):  # M-13
    r = client.get(URL, {"producto": arroz[0].pk})
    assert r.status_code == 302 and "/cuentas/ingresar/" in r["Location"]
    assert "producto" in r["Location"]  # al volver, retoma donde estaba (next=…)


# ───────────── Entradas desde la comparación y la cabecera ─────────────


def test_la_comparacion_lleva_a_registrar_ese_producto(client, reportante, arroz, tiendas):
    prod, p500, _ = arroz
    _registrar(reportante, p500, tiendas[0])
    html = client.get(reverse("comparacion:comparar", args=[prod.pk])).content.decode()
    assert f"{URL}?producto={prod.pk}" in html


def test_cada_tarjeta_ofrece_registrar_el_precio_de_esa_tienda_y_presentacion(
    client, reportante, arroz, tiendas
):
    prod, p500, _ = arroz
    _registrar(reportante, p500, tiendas[0])
    html = client.get(reverse("comparacion:comparar", args=[prod.pk])).content.decode()
    assert f"presentacion={p500.pk}" in html and f"establecimiento={tiendas[0].pk}" in html


@pytest.mark.parametrize("ruta", ["comparacion:productos", "establecimientos:directorio"])
def test_registrar_precio_esta_siempre_a_la_vista_fuera_del_menu(client, ruta):
    html = client.get(reverse(ruta)).content.decode()
    cabecera = html[html.index('<header class="cabecera"') : html.index("</header>")]
    nav = cabecera[cabecera.index('id="nav-principal"') : cabecera.index("</nav>")]
    assert 'class="btn btn-registrar"' in cabecera
    assert reverse("precios:registrar") not in nav  # no escondido tras la hamburguesa


def test_el_boton_de_registrar_tambien_esta_con_sesion_iniciada(client, reportante):
    client.force_login(reportante)
    html = client.get(reverse("comparacion:productos")).content.decode()
    assert 'class="btn btn-registrar"' in html


def test_en_la_portada_registrar_precio_es_el_boton_grande_del_centro(client):
    # La barra queda limpia en la portada: el botón principal vive en el centro (PUX-01, M-01)
    html = client.get(reverse("comparacion:inicio")).content.decode()
    centro = html.split('class="hero-acciones"')[1].split("</div>")[0]
    assert reverse("precios:registrar") in centro and "btn-grande" in centro


# ───────────── La comparación muestra los precios primero ─────────────


def _comparacion(client, producto, **params):
    return client.get(reverse("comparacion:comparar", args=[producto.pk]), params).content.decode()


def _dos_precios(reportante, arroz, tiendas):
    _, p500, p1kg = arroz
    _registrar(reportante, p500, tiendas[0], "2500")
    _registrar(reportante, p1kg, tiendas[1], "4800")


def test_los_filtros_de_la_comparacion_van_plegados_para_ver_primero_los_precios(
    client, reportante, arroz, tiendas
):
    _dos_precios(reportante, arroz, tiendas)
    html = _comparacion(client, arroz[0])
    detalles = re.search(r'<details class="panel-plegable panel-filtros"([^>]*)>', html)
    assert detalles and "open" not in detalles.group(1)
    assert 'id="filtros-comparacion"' in html  # siguen ahí, solo plegados
    assert html.index("panel-filtros") < html.index('id="resultados"')


def test_con_un_filtro_activo_el_panel_se_abre_solo(client, reportante, arroz, tiendas):
    _dos_precios(reportante, arroz, tiendas)
    html = _comparacion(client, arroz[0], precio_min="3000")
    detalles = re.search(r'<details class="panel-plegable panel-filtros"([^>]*)>', html)
    assert detalles and "open" in detalles.group(1)
    assert "· activo" in html
