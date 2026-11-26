"""Asistente de compras como chat: lista escrita o adjunta → tienda más barata (ADR-0027 a 0030).

M-24 (faltantes correctos), M-06 (orden declarado), M-15 (sin datos del reportante), EC-14 (las
cifras salen del dominio).
"""

from decimal import Decimal
from pathlib import Path

import pytest
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.catalogo.models import Categoria, Presentacion, Producto
from apps.precios import services

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _cache_limpia():
    cache.clear()


@pytest.fixture
def leche(db):
    cat = Categoria.objects.create(nombre="Lácteos")
    prod = Producto.objects.create(nombre="Leche", nombre_normalizado="leche", categoria=cat)
    return prod, Presentacion.objects.create(producto=prod, cantidad=Decimal("1"), unidad="L")


def _precio(autor, presentacion, tienda, precio):
    services.registrar_reporte(
        autor=autor, presentacion_id=presentacion.pk, establecimiento_id=tienda.pk, precio=precio
    )


def _decir(client, texto="", archivo=None, htmx=False):
    datos = {"mensaje": texto}
    if archivo is not None:
        datos["archivo"] = archivo
    extra = {"HTTP_HX_REQUEST": "true"} if htmx else {}
    return client.post(reverse("canasta:enviar"), datos, **extra)


@pytest.fixture
def mercado(reportante, arroz, leche, tiendas):
    """Rosa tiene arroz barato y no tiene leche; Súper tiene los dos."""
    _, _, p1kg = arroz
    rosa, super_ = tiendas
    _precio(reportante, p1kg, rosa, 5000)
    _precio(reportante, p1kg, super_, 7000)
    _precio(reportante, leche[1], super_, 4000)
    return rosa, super_


def test_la_pagina_saluda_e_invita_a_pasar_la_lista(client):
    html = client.get(reverse("canasta:inicio")).content.decode()
    assert "Soy K-nasta" in html and "lista de ejemplo" in html
    assert 'type="file"' in html and "<textarea" in html


def test_una_lista_escrita_recomienda_la_tienda_que_lo_tiene_todo(client, mercado):
    html = _decir(client, "2 kg arroz, 1 L leche").content.decode()
    assert "Te conviene Súper Quindío" in html
    assert "$18.000" in html  # 2 kg × 7.000 + 1 L × 4.000
    assert "Tiene todo (2 de 2)" in html


def test_la_tienda_mas_barata_incompleta_no_gana_por_sumar_cero(client, mercado):
    html = _decir(client, "arroz, leche").content.decode()
    assert html.index("Súper Quindío") < html.index("Tienda Doña Rosa")  # M-24
    assert "Tienda Doña Rosa" in html and "faltan 1" in html


def test_un_archivo_de_texto_adjunto_se_lee_como_lista(client, mercado):
    archivo = SimpleUploadedFile("mercado.txt", b"2 kg arroz\n1 L leche", "text/plain")
    html = _decir(client, "", archivo).content.decode()
    assert "📎 mercado.txt" in html and "Te conviene Súper Quindío" in html


def test_una_foto_adjunta_explica_que_aun_no_se_leen_fotos(client, mercado):
    foto = SimpleUploadedFile("lista.jpg", b"\xff\xd8\xff", "image/jpeg")
    html = _decir(client, "", foto).content.decode()
    assert "Todavía no sé leer fotos" in html


def test_ordenar_por_menor_total_cambia_el_orden_y_lo_declara(client, mercado):
    _decir(client, "arroz, leche")
    html = _decir(client, "menor total").content.decode()
    assert "Ordenado por: menor total" in html
    tarjeta = html.split('class="cc-res es-mejor"')[1]
    assert tarjeta.index("Tienda Doña Rosa") < tarjeta.index("Ver las otras")


def test_agregar_y_quitar_productos_de_la_lista(client, mercado):
    _decir(client, "arroz")
    html = _decir(client, "agrega leche").content.decode()
    assert "Súper Quindío" in html and "2 de 2" in html
    html = _decir(client, "quita la leche").content.decode()
    assert "Quité Leche" in html


def test_producto_que_no_existe_se_dice_sin_inventar(client, mercado):
    html = _decir(client, "unicornio azul").content.decode()
    assert "No encontré esos productos en el catálogo: unicornio azul" in html


def test_mensaje_sin_productos_pide_la_lista(client):
    html = _decir(client, "hola").content.decode()
    assert "No encontré" in html or "No pude leer" in html


def test_empezar_de_nuevo_limpia_la_conversacion(client, mercado):
    _decir(client, "arroz")
    html = _decir(client, "empezar de nuevo").content.decode()
    assert "empecemos de nuevo" in html
    assert "Tienda Doña Rosa" not in html.split("empecemos de nuevo")[1]


def test_nueva_conversacion_borra_todo(client, mercado):
    _decir(client, "arroz")
    html = client.post(reverse("canasta:enviar"), {"reiniciar": "1"}).content.decode()
    assert "Soy K-nasta" in html and "Tienda Doña Rosa" not in html


def test_con_htmx_devuelve_solo_la_conversacion(client, mercado):
    html = _decir(client, "arroz", htmx=True).content.decode()
    assert "<html" not in html and "burbuja" in html


def test_el_unico_resultado_con_tarjeta_es_el_ultimo(client, mercado):
    _decir(client, "arroz")
    html = _decir(client, "arroz, leche").content.decode()
    assert html.count('class="cc-res es-mejor"') == 1


def test_la_respuesta_no_expone_datos_de_quien_reporto(client, reportante, mercado):
    html = _decir(client, "arroz, leche").content.decode()
    assert reportante.username not in html  # M-15


def test_un_mensaje_vacio_no_hace_nada(client):
    html = _decir(client, "   ").content.decode()
    assert "Soy K-nasta" in html


def test_cantidad_con_unidad_que_no_corresponde_avisa_y_usa_la_del_producto(client, mercado):
    html = _decir(client, "2 litros de arroz").content.decode()
    assert "no se mide en L; usé kg" in html


# --- disponible en cualquier página (botón flotante) -------------------------------------------
@pytest.mark.parametrize(
    "ruta",
    [
        "comparacion:inicio",
        "comparacion:productos",
        "establecimientos:directorio",
        "cuentas:ingresar",
    ],
)
def test_el_boton_del_asistente_esta_en_cualquier_pagina(client, ruta):
    html = client.get(reverse(ruta)).content.decode()
    assert "asistente-lanzador" in html and 'href="/asistente/"' in html  # enlace sin JavaScript
    assert 'aria-controls="asistente-panel"' in html and 'role="dialog"' in html


def test_el_asistente_no_es_un_modulo_del_menu(client):
    html = client.get(reverse("comparacion:inicio")).content.decode()
    menu = html.split('id="nav-principal"')[1].split("</nav>")[0]
    assert "Asistente" not in menu


def test_el_cuerpo_del_chat_se_pide_al_abrirlo_no_en_la_carga(client):
    html = client.get(reverse("comparacion:inicio")).content.decode()
    assert 'hx-trigger="asistente:abrir once"' in html
    assert "chat-mensaje" not in html  # el formulario aún no viaja con la página
    panel = client.get(reverse("canasta:cuerpo")).content.decode()
    assert "chat-mensaje" in panel and "<html" not in panel


def test_en_la_pagina_completa_del_asistente_no_se_duplica_el_boton(client):
    html = client.get(reverse("canasta:inicio")).content.decode()
    assert "asistente-lanzador" not in html and html.count('id="chat-hilo"') == 1


def test_la_conversacion_sigue_al_cambiar_de_pagina(client, mercado):
    _decir(client, "2 kg arroz, 1 L leche")
    panel = client.get(reverse("canasta:cuerpo")).content.decode()
    assert "Te conviene Súper Quindío" in panel


# --- nombre y etiqueta «IA» (honestidad: solo cuando de verdad usa IA) --------------------------
def test_se_llama_k_nasta_y_trae_su_ilustracion(client):
    html = client.get(reverse("comparacion:inicio")).content.decode()
    assert "K-nasta" in html and "knasta-96.png" in html
    pagina = client.get(reverse("canasta:inicio")).content.decode()
    assert "<h1" in pagina and "K-nasta" in pagina


def test_sin_ia_activa_no_se_muestra_la_etiqueta_ia(client, settings):
    settings.INTEGRACIONES = {**settings.INTEGRACIONES, "ASISTENTE_IA_ACTIVO": True}  # sin clave
    settings.INTEGRACIONES["ANTHROPIC_API_KEY"] = ""
    html = client.get(reverse("comparacion:inicio")).content.decode()
    assert "etiqueta-ia" not in html


def test_con_ia_activa_la_etiqueta_aparece_en_el_boton_y_el_encabezado(client, settings):
    settings.INTEGRACIONES = {
        **settings.INTEGRACIONES,
        "ASISTENTE_IA_ACTIVO": True,
        "ANTHROPIC_API_KEY": "clave-de-prueba",
    }
    html = client.get(reverse("comparacion:inicio")).content.decode()
    assert html.count('class="etiqueta-ia"') == 2


def test_el_boton_se_esconde_mientras_el_chat_esta_abierto():
    css = (Path(__file__).resolve().parents[2] / "static/css/app.css").read_text(encoding="utf-8")
    assert "body.asistente-abierto .asistente-lanzador { display: none; }" in css


def test_el_cierre_del_asistente_no_comparte_atributo_con_el_escaner(client):
    html = client.get(reverse("comparacion:inicio")).content.decode()
    assert "data-asistente-cerrar" in html


# --- el detalle de cada producto se explica solo ------------------------------------------------
def test_el_detalle_dice_cuanto_pediste_y_cuantos_empaques_llevas(
    client, reportante, arroz, tiendas
):
    _, p500, _ = arroz
    _precio(reportante, p500, tiendas[0], 2650)  # empaque de 500 g
    html = _decir(client, "1 kg arroz").content.decode()
    assert "pediste 1 kg" in html and "llevas 2 empaques de 500 g" in html
    assert "paga el empaque completo" in html  # aclara que el costo es por tu cantidad


def test_si_el_empaque_alcanza_exacto_no_habla_de_varios(client, reportante, arroz, tiendas):
    _, _, p1kg = arroz
    _precio(reportante, p1kg, tiendas[0], 8000)
    html = _decir(client, "1 kg arroz").content.decode()
    assert "pediste 1 kg" in html and "empaque de 1 kg" in html and "llevas 2" not in html


def test_las_cantidades_pequenas_se_muestran_en_gramos_o_mililitros(
    client, reportante, arroz, tiendas
):
    _, p500, _ = arroz
    _precio(reportante, p500, tiendas[0], 2650)
    html = _decir(client, "250 g arroz").content.decode()
    assert "pediste 250 g" in html and "pediste 0,25 kg" not in html
