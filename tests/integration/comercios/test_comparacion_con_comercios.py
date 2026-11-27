"""El módulo comercial en la comparación, por el puerto (ADR-012, ADR-018, ADR-014).

- El precio oficial verificado y vigente es el principal; con 2 o más reportes en 7 días que
  difieren más de 10 % aparece «Usuarios reportan $X» y la confianza baja a media.
- Neutralidad: el orden es el mismo con y sin promociones (EC-06, M-06 = 100 %).
- Privacidad: la API pública no expone datos del comercio ni de quien reporta (M-15).
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.comercios import selectors as comercios_selectors
from apps.comercios import services
from apps.comercios.models import PrecioOficial
from apps.comparacion.domain.extensiones import PUNTO_DATOS_COMERCIALES
from apps.comparacion.selectors import comparar_filas
from core import extensiones
from tests.integration.comercios.pdf import pdfs

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def _publicar(usuario, presentacion, precio):
    return services.publicar_precio_oficial(
        usuario=usuario, presentacion_id=presentacion.pk, precio=Decimal(precio)
    )


def _promocion(usuario, presentacion, **extra):
    datos = {
        "usuario": usuario,
        "presentacion_id": presentacion.pk,
        "tipo": "descuento_porcentual",
        "porcentaje": Decimal("50"),
        "inicio": timezone.now() - timedelta(days=1),
        "fin": timezone.now() + timedelta(days=7),
        "motivo": "temporada",
        "condiciones": "Hasta agotar existencias.",
    }
    return services.crear_promocion(**(datos | extra))


def _fila_de(producto, local):
    return next(
        f for f in comparar_filas(producto.pk) if f.resultado.establecimiento_id == local.pk
    )


# ---------- ADR-018: oficial frente a reportado ----------


def test_el_oficial_verificado_reemplaza_al_reporte_de_su_tienda(
    comercio, duena, tiendas, arroz, reportar
):
    reportar(arroz[2], tiendas[0], "4500")
    _publicar(duena, arroz[2], "4100")
    filas = [
        f for f in comparar_filas(arroz[0].pk) if f.resultado.establecimiento_id == tiendas[0].pk
    ]
    assert len(filas) == 1  # una sola fila por (local, presentación)
    fila = filas[0]
    assert fila.es_oficial and fila.resultado.fuente == "comercio"
    assert fila.resultado.precio == Decimal("4100") and fila.resultado.confianza == "alta"
    assert fila.usuarios_reportan is None


def test_el_oficial_aparece_aunque_nadie_haya_reportado_en_su_tienda(comercio, duena, arroz):
    _publicar(duena, arroz[2], "4100")
    filas = comparar_filas(arroz[0].pk)
    assert len(filas) == 1 and filas[0].es_oficial
    assert filas[0].ancla == f"tpo-{filas[0].resultado.establecimiento_id}-{arroz[2].pk}"


def test_dos_reportes_discrepantes_en_7_dias_muestran_la_advertencia(
    comercio, duena, tiendas, arroz, reportar
):
    _publicar(duena, arroz[2], "4000")
    reportar(arroz[2], tiendas[0], "5000", dias=3)
    reportar(arroz[2], tiendas[0], "5200", dias=1)
    fila = _fila_de(arroz[0], tiendas[0])
    assert fila.usuarios_reportan == Decimal("5200")
    assert fila.usuarios_reportan_texto == "Usuarios reportan $5.200"
    assert fila.resultado.confianza == "media"
    assert fila.resultado.precio == Decimal("4000")  # sigue siendo el principal


def test_un_solo_reporte_discrepante_no_basta(comercio, duena, tiendas, arroz, reportar):
    _publicar(duena, arroz[2], "4000")
    reportar(arroz[2], tiendas[0], "5000", dias=1)
    assert _fila_de(arroz[0], tiendas[0]).usuarios_reportan is None


def test_un_oficial_vencido_deja_ver_el_reporte(comercio, duena, tiendas, arroz, reportar):
    _publicar(duena, arroz[2], "4000")
    PrecioOficial.objects.update(confirmado_en=timezone.now() - timedelta(days=31))
    reportar(arroz[2], tiendas[0], "4600")
    fila = _fila_de(arroz[0], tiendas[0])
    assert not fila.es_oficial and fila.resultado.precio == Decimal("4600")


def test_confirmar_vigencia_vuelve_a_mostrar_el_oficial(
    comercio, duena, tiendas, arroz, django_capture_on_commit_callbacks
):
    _publicar(duena, arroz[2], "4000")
    PrecioOficial.objects.update(confirmado_en=timezone.now() - timedelta(days=31))
    assert comparar_filas(arroz[0].pk) == []
    with django_capture_on_commit_callbacks(execute=True):
        services.confirmar_vigencia(usuario=duena)  # invalida la caché al confirmar
    assert comparar_filas(arroz[0].pk)[0].es_oficial


def test_un_perfil_rechazado_o_pendiente_nunca_publica_en_la_comparacion(
    duena, tiendas, arroz, moderador
):
    perfil = services.crear_perfil(
        usuario=duena, establecimiento_id=tiendas[0].pk, nombre_contacto="R", **pdfs()
    )
    PrecioOficial.objects.create(  # aun si existiera, por error, un precio de un no verificado
        perfil=perfil, presentacion=arroz[2], precio=1, confirmado_en=timezone.now()
    )
    assert comparar_filas(arroz[0].pk) == []


def test_publicar_invalida_la_cache_de_la_comparacion(
    comercio, duena, tiendas, arroz, reportar, django_capture_on_commit_callbacks
):
    reportar(arroz[2], tiendas[0], "4500")
    assert _fila_de(arroz[0], tiendas[0]).resultado.fuente == "reportante"  # queda en caché
    with django_capture_on_commit_callbacks(execute=True):
        _publicar(duena, arroz[2], "4100")
    assert _fila_de(arroz[0], tiendas[0]).resultado.fuente == "comercio"  # EC-02


# ---------- EC-06 / M-06: neutralidad con y sin promociones ----------


def test_el_orden_es_el_mismo_con_y_sin_promociones(
    comercio, duena, tiendas, arroz, reportar, django_capture_on_commit_callbacks
):  # EC-06, M-06
    # Súper Quindío es más barato; una promoción del 50 % en Doña Rosa NO la adelanta
    reportar(arroz[2], tiendas[1], "3800")
    _publicar(duena, arroz[2], "4000")
    antes = [f.resultado.establecimiento_id for f in comparar_filas(arroz[0].pk)]
    with django_capture_on_commit_callbacks(execute=True):  # la promoción invalida la caché
        _promocion(duena, arroz[2])
    filas = comparar_filas(arroz[0].pk)
    assert (
        [f.resultado.establecimiento_id for f in filas] == antes == [tiendas[1].pk, tiendas[0].pk]
    )
    promo = filas[1]
    assert promo.resultado.es_promocion and promo.promociones[0].precio_efectivo == Decimal("2000")
    assert promo.resultado.precio == Decimal("4000")  # el que ordena es el precio regular


def test_la_promocion_es_etiqueta_en_la_tarjeta(client, comercio, duena, arroz):  # EC-06
    _publicar(duena, arroz[2], "4000")
    _promocion(duena, arroz[2])
    html = client.get(reverse("comparacion:comparar", args=[arroz[0].pk])).content.decode()
    assert "Promoción" in html and "50 % de descuento" in html
    assert "Hasta agotar existencias." in html  # condiciones junto al precio (Ley 1480)
    assert "Oficial" in html


def test_una_promocion_terminada_desaparece(comercio, duena, arroz):
    _publicar(duena, arroz[2], "4000")
    promo = _promocion(duena, arroz[2])
    services.finalizar_promocion(usuario=duena, promocion_id=promo.pk)
    assert not comparar_filas(arroz[0].pk)[0].resultado.es_promocion


# ---------- API pública: aditiva y sin datos privados ----------


def test_la_api_publica_trae_el_arreglo_promociones_y_conserva_es_promocion(
    api, comercio, duena, arroz
):
    _publicar(duena, arroz[2], "4000")
    _promocion(duena, arroz[2], tipo="pague_x_lleve_y", porcentaje=None, pague=2, lleve=3)
    datos = api.get(reverse("api-comparacion", args=[arroz[0].pk])).json()
    assert datos["resultados"][0]["es_promocion"] is True
    assert datos["resultados"][0]["fuente"] == "comercio"
    promo = datos["promociones"][0]
    assert promo["descripcion"] == "Lleve 3, pague 2"
    assert promo["establecimiento"] == "Tienda Doña Rosa"
    assert set(promo) == {
        "establecimiento_id",
        "establecimiento",
        "presentacion",
        "tipo",
        "descripcion",
        "precio_efectivo",
        "precio_efectivo_unitario",
        "unidad_base",
        "inicio",
        "fin",
        "motivo",
        "condiciones",
        "fecha_vencimiento_producto",
    }


def test_la_api_publica_no_expone_al_comercio_ni_a_quien_reporta(
    api, comercio, duena, moderador, tiendas, arroz, reportar, reportante
):  # M-15
    _publicar(duena, arroz[2], "4000")
    _promocion(duena, arroz[2])
    reportar(arroz[1], tiendas[1], "2000")
    texto = api.get(reverse("api-comparacion", args=[arroz[0].pk])).content.decode()
    for privado in (
        duena.username,
        duena.email,
        reportante.username,
        moderador.username,
        "3001234567",  # teléfono del perfil
        comercio.codigo_verificacion,
        *(d.sha256 for d in comercio.documentos.all()),  # constancia de la evidencia (ADR-0034)
    ):
        assert privado not in texto


def test_la_pagina_publica_tampoco_muestra_datos_del_comercio(client, comercio, duena, arroz):
    _publicar(duena, arroz[2], "4000")  # M-15
    html = client.get(reverse("comparacion:comparar", args=[arroz[0].pk])).content.decode()
    assert "3001234567" not in html and "NIT 900123456-7" not in html


# ---------- Eficiencia: queries constantes (sin N+1) ----------


def test_la_comparacion_no_hace_n_mas_1_con_varios_comercios(
    comercio,
    duena,
    crear_usuario,
    verificar,
    tiendas,
    arroz,
    reportar,
    django_assert_max_num_queries,
):
    _publicar(duena, arroz[1], "2000")
    _publicar(duena, arroz[2], "4000")
    _promocion(duena, arroz[2])
    otro = crear_usuario("otro")
    verificar(otro, tiendas[1])
    _publicar(otro, arroz[2], "3900")
    _publicar(otro, arroz[1], "1900")
    reportar(arroz[2], tiendas[1], "4500")
    with django_assert_max_num_queries(8):
        assert len(comparar_filas(arroz[0].pk)) == 4


# ---------- El puerto: el núcleo no depende del módulo comercial (EC-05) ----------


def test_sin_la_extension_registrada_la_comparacion_sigue_igual_que_en_el_nucleo(
    comercio, duena, tiendas, arroz, reportar
):
    reportar(arroz[2], tiendas[0], "4500")
    _publicar(duena, arroz[2], "4100")
    extensiones.retirar(PUNTO_DATOS_COMERCIALES, comercios_selectors.EXTENSION)
    try:
        fila = _fila_de(arroz[0], tiendas[0])
        assert fila.resultado.fuente == "reportante" and not fila.es_oficial
    finally:
        extensiones.registrar(PUNTO_DATOS_COMERCIALES, comercios_selectors.EXTENSION)


def test_si_la_extension_falla_la_comparacion_muestra_los_reportes(
    tiendas, arroz, reportar, monkeypatch, caplog
):
    reportar(arroz[2], tiendas[0], "4500")

    def falla(*_args, **_kwargs):
        raise RuntimeError("caída del módulo comercial")

    monkeypatch.setattr(comercios_selectors.EXTENSION, "datos_para", falla)
    filas = comparar_filas(arroz[0].pk)
    assert len(filas) == 1 and filas[0].resultado.fuente == "reportante"
    assert "extensión" in caplog.text


def test_el_modulo_comercial_esta_registrado_al_arrancar():
    assert comercios_selectors.EXTENSION in extensiones.extensiones(PUNTO_DATOS_COMERCIALES)
