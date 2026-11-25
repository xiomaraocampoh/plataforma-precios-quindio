"""Portal HTMX /comercios/ y API /api/v1/comercios/: permisos por rol, aislamiento entre
comercios, throttling (M-13) y accesibilidad de los formularios (M-03)."""

import re
from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.throttling import ScopedRateThrottle

from apps.comercios import services
from apps.comercios.models import PerfilComercio, PrecioOficial, Promocion

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

HTMX = {"HTTP_HX_REQUEST": "true"}


def _referencias_rotas(html: str) -> list[str]:
    ids = set(re.findall(r'\bid="([^"]+)"', html))
    citados = re.findall(r'aria-(?:describedby|labelledby|controls)="([^"]+)"', html)
    return sorted({ref for grupo in citados for ref in grupo.split()} - ids)


def _controles_sin_etiqueta(html: str) -> list[str]:
    etiquetas = set(re.findall(r'<label for="([^"]+)"', html))
    controles = re.findall(
        r'<(?:input|select|textarea)\b(?![^>]*type="hidden")[^>]*\bid="([^"]+)"', html
    )
    return sorted(set(controles) - etiquetas)


# ---------- Portal: permisos y flujo ----------


def test_el_portal_pide_ingresar(client):
    respuesta = client.get(reverse("comercios:inicio"))
    assert respuesta.status_code == 302 and "ingresar" in respuesta.url


def test_quien_no_tiene_perfil_ve_el_formulario_accesible(client, duena, tiendas):
    client.force_login(duena)
    html = client.get(reverse("comercios:inicio")).content.decode()
    assert "Crea el perfil de tu comercio" in html and "Tienda Doña Rosa" in html
    assert _controles_sin_etiqueta(html) == []  # M-03: cada control con su label
    assert _referencias_rotas(html) == []
    assert 'aria-live="polite"' in html and "hx-disabled-elt" in html


def test_crear_el_perfil_por_htmx_devuelve_la_seccion_con_el_codigo(client, duena, tiendas):
    client.force_login(duena)
    respuesta = client.post(
        reverse("comercios:crear_perfil"),
        {
            "establecimiento": tiendas[0].pk,
            "nombre_contacto": "Rosa",
            "telefono": "",
            "evidencia": "NIT 1",
        },
        **HTMX,
    )
    html = respuesta.content.decode()
    assert respuesta.status_code == 200 and 'id="sec-perfil"' in html
    assert "en revisión" in html and PerfilComercio.objects.get().codigo_verificacion in html
    assert "<html" not in html  # fragmento, no página completa


def test_el_perfil_con_datos_vacios_muestra_errores_por_campo(client, duena, tiendas):
    client.force_login(duena)
    html = client.post(reverse("comercios:crear_perfil"), {}, **HTMX).content.decode()
    assert html.count('class="error"') >= 3 and _referencias_rotas(html) == []
    assert not PerfilComercio.objects.exists()


def test_la_bandeja_de_verificacion_es_solo_de_moderacion(client, duena, moderador):
    client.force_login(duena)
    assert client.get(reverse("comercios:verificacion")).status_code == 403
    client.force_login(moderador)
    assert client.get(reverse("comercios:verificacion")).status_code == 200


def test_moderacion_verifica_desde_la_bandeja(client, duena, tiendas, moderador):
    perfil = services.crear_perfil(
        usuario=duena, establecimiento_id=tiendas[0].pk, nombre_contacto="R", evidencia="NIT 7"
    )
    client.force_login(moderador)
    html = client.get(reverse("comercios:verificacion")).content.decode()
    assert "NIT 7" in html and _controles_sin_etiqueta(html) == []
    respuesta = client.post(
        reverse("comercios:decidir_perfil", args=[perfil.pk]), {"decision": "aprobar"}, **HTMX
    )
    assert "Decisión registrada." in respuesta.content.decode()
    perfil.refresh_from_db()
    assert perfil.verificado and perfil.verificado_por == moderador


def test_un_reportante_no_decide_sobre_un_perfil(client, duena, crear_usuario, tiendas):
    perfil = services.crear_perfil(
        usuario=duena, establecimiento_id=tiendas[0].pk, nombre_contacto="R", evidencia="x"
    )
    client.force_login(crear_usuario("curioso"))
    respuesta = client.post(
        reverse("comercios:decidir_perfil", args=[perfil.pk]), {"decision": "aprobar"}
    )
    assert respuesta.status_code == 403
    assert PerfilComercio.objects.get(pk=perfil.pk).estado == "pendiente"


def test_el_comercio_verificado_publica_desde_el_portal(client, comercio, duena, arroz):
    client.force_login(duena)
    html = client.get(reverse("comercios:inicio")).content.decode()
    assert "Precios oficiales" in html and _controles_sin_etiqueta(html) == []
    respuesta = client.post(
        reverse("comercios:publicar_precio"),
        {"presentacion": arroz[2].pk, "precio": "4100"},
        **HTMX,
    )
    assert "Precio oficial publicado" in respuesta.content.decode()
    assert PrecioOficial.objects.get().precio == Decimal("4100")


def test_un_comercio_pendiente_ve_su_codigo_y_no_publica(client, duena, tiendas, arroz):
    perfil = services.crear_perfil(
        usuario=duena, establecimiento_id=tiendas[0].pk, nombre_contacto="R", evidencia="x"
    )
    client.force_login(duena)
    assert perfil.codigo_verificacion in client.get(reverse("comercios:inicio")).content.decode()
    respuesta = client.post(
        reverse("comercios:publicar_precio"), {"presentacion": arroz[2].pk, "precio": "1"}, **HTMX
    )
    assert "aún no está verificado" in respuesta.content.decode()
    assert not PrecioOficial.objects.exists()


def test_por_el_portal_un_comercio_no_retira_el_precio_de_otro(
    client, comercio, duena, crear_usuario, tiendas, verificar, arroz
):
    oficial = services.publicar_precio_oficial(
        usuario=duena, presentacion_id=arroz[2].pk, precio=Decimal(4000)
    )
    otro = crear_usuario("otro")
    verificar(otro, tiendas[1])
    client.force_login(otro)
    respuesta = client.post(reverse("comercios:retirar_precio", args=[oficial.pk]), **HTMX)
    assert "no es de tu comercio" in respuesta.content.decode()
    assert PrecioOficial.objects.filter(pk=oficial.pk).exists()


def test_confirmar_vigencia_con_un_toque(client, comercio, duena, arroz):
    services.publicar_precio_oficial(usuario=duena, presentacion_id=arroz[2].pk, precio=Decimal(1))
    client.force_login(duena)
    html = client.post(reverse("comercios:confirmar_vigencia"), **HTMX).content.decode()
    assert "1 precio sigue vigente" in html


def test_crear_una_promocion_desde_el_portal(client, comercio, duena, arroz):
    services.publicar_precio_oficial(
        usuario=duena, presentacion_id=arroz[2].pk, precio=Decimal(4000)
    )
    client.force_login(duena)
    hoy = timezone.localdate()
    respuesta = client.post(
        reverse("comercios:crear_promocion"),
        {
            "presentacion": arroz[2].pk,
            "tipo": "pague_x_lleve_y",
            "lleve": "3",
            "pague": "2",
            "inicio": hoy.isoformat(),
            "fin": (hoy + timedelta(days=7)).isoformat(),
            "motivo": "temporada",
            "condiciones": "Hasta agotar existencias.",
        },
        **HTMX,
    )
    html = respuesta.content.decode()
    assert "Promoción publicada." in html and "Lleve 3, pague 2" in html
    assert Promocion.objects.get().fin.date() == hoy + timedelta(days=8)  # fin inclusive


def test_el_menu_de_la_cuenta_enlaza_el_portal(client, comercio, duena, moderador):
    client.force_login(duena)
    assert "Mi comercio" in client.get(reverse("comparacion:inicio")).content.decode()
    client.force_login(moderador)
    assert "Verificar comercios" in client.get(reverse("comparacion:inicio")).content.decode()


# ---------- API: rol, verificación, aislamiento y throttling ----------


def test_la_api_exige_autenticacion(api):
    assert api.get(reverse("api-comercios-precios")).status_code in (401, 403)
    assert api.post(reverse("api-comercios-precios"), {}).status_code in (401, 403)  # M-13


def test_la_api_exige_el_rol_comercio(api, duena):
    api.force_authenticate(duena)  # reportante sin perfil verificado
    assert api.get(reverse("api-comercios-precios")).status_code == 403


def test_la_api_publica_y_lista_solo_lo_propio(
    api, comercio, duena, crear_usuario, tiendas, verificar, arroz
):
    otro = crear_usuario("otro")
    verificar(otro, tiendas[1])
    services.publicar_precio_oficial(usuario=otro, presentacion_id=arroz[1].pk, precio=Decimal(9))
    api.force_authenticate(duena)
    creado = api.post(
        reverse("api-comercios-precios"), {"presentacion": arroz[2].pk, "precio": "4100"}
    )
    assert creado.status_code == 201
    lista = api.get(reverse("api-comercios-precios")).json()
    assert [p["presentacion"] for p in lista] == [arroz[2].pk]


def test_la_api_no_termina_la_promocion_de_otro(
    api, comercio, duena, crear_usuario, tiendas, verificar, arroz
):
    services.publicar_precio_oficial(
        usuario=duena, presentacion_id=arroz[2].pk, precio=Decimal(4000)
    )
    promo = services.crear_promocion(
        usuario=duena,
        presentacion_id=arroz[2].pk,
        tipo="descuento_porcentual",
        porcentaje=Decimal("10"),
        inicio=timezone.now(),
        fin=timezone.now() + timedelta(days=2),
        motivo="temporada",
        condiciones="x",
    )
    otro = crear_usuario("otro")
    verificar(otro, tiendas[1])
    api.force_authenticate(otro)
    respuesta = api.post(reverse("api-comercios-terminar-promocion", args=[promo.pk]))
    assert respuesta.status_code == 400
    assert Promocion.objects.get(pk=promo.pk).activa


def test_la_api_valida_la_promocion_con_el_dominio(api, comercio, duena, arroz):
    services.publicar_precio_oficial(
        usuario=duena, presentacion_id=arroz[2].pk, precio=Decimal(4000)
    )
    api.force_authenticate(duena)
    respuesta = api.post(
        reverse("api-comercios-promociones"),
        {
            "presentacion": arroz[2].pk,
            "tipo": "descuento_porcentual",
            "porcentaje": "100",
            "inicio": timezone.now().isoformat(),
            "fin": (timezone.now() + timedelta(days=1)).isoformat(),
            "motivo": "temporada",
            "condiciones": "x",
        },
        format="json",
    )
    assert respuesta.status_code == 400 and not Promocion.objects.exists()


def test_la_api_del_perfil_no_expone_datos_de_contacto(api, comercio, duena):  # M-15
    api.force_authenticate(duena)
    datos = api.get(reverse("api-comercios-perfil")).json()
    assert set(datos) == {"establecimiento_id", "establecimiento", "estado", "verificado_en"}


def test_la_api_de_comercios_tiene_su_throttle_scope(api, comercio, duena, monkeypatch):  # M-13
    monkeypatch.setitem(ScopedRateThrottle.THROTTLE_RATES, "comercios", "2/min")
    api.force_authenticate(duena)
    estados = [api.get(reverse("api-comercios-perfil")).status_code for _ in range(3)]
    assert estados == [200, 200, 429]


def test_el_esquema_openapi_documenta_la_api_de_comercios(client):
    esquema = client.get(reverse("schema")).content.decode()
    assert "/api/v1/comercios/precios/" in esquema and "TipoPromocionEnum" in esquema
