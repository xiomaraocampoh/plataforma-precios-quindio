"""RF-14 «Sigue igual»: renueva la vigencia, suma confianza, idempotente y con límite por hora."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from apps.comparacion.selectors import comparar_producto
from apps.precios import services
from apps.precios.models import ConfirmacionPrecio

pytestmark = pytest.mark.integration


@pytest.fixture
def vecina(django_user_model):
    return django_user_model.objects.create_user(username="vecina", password="x-clave-segura-1")


@pytest.fixture
def reporte(reportante, arroz, tiendas):
    _, p500, _ = arroz
    rosa, _ = tiendas
    return services.registrar_reporte(
        autor=reportante, presentacion_id=p500.pk, establecimiento_id=rosa.pk, precio=Decimal(2500)
    )


def _url(reporte):
    return reverse("precios:sigue_igual", args=[reporte.pk])


def test_anonimo_no_ve_el_boton_y_no_puede_confirmar(client, reporte, arroz):
    producto, _, _ = arroz
    html = client.get(reverse("comparacion:comparar", args=[producto.pk])).content.decode()
    assert "Sigue igual" not in html
    assert client.post(_url(reporte)).status_code == 302  # al ingreso


def test_otra_persona_confirma_una_vez_por_dia(client, vecina, reporte, arroz):
    producto, _, _ = arroz
    client.force_login(vecina)
    html = client.get(reverse("comparacion:comparar", args=[producto.pk])).content.decode()
    assert "Sigue igual" in html
    primera = client.post(_url(reporte), HTTP_HX_REQUEST="true").content.decode()
    segunda = client.post(_url(reporte), HTTP_HX_REQUEST="true").content.decode()
    assert "¡Gracias! Confirmaste que sigue igual." in primera
    assert "Ya lo confirmaste hoy." in segunda
    assert ConfirmacionPrecio.objects.filter(reporte=reporte, usuario=vecina).count() == 1


def test_el_autor_no_puede_confirmar_su_propio_precio(client, reportante, reporte, arroz):
    producto, _, _ = arroz
    with pytest.raises(ValidationError, match="reportaste tú"):
        services.confirmar_precio(usuario=reportante, reporte_id=reporte.pk)
    client.force_login(reportante)
    html = client.get(reverse("comparacion:comparar", args=[producto.pk])).content.decode()
    assert "Sigue igual" not in html  # no se le ofrece el botón


def test_la_confirmacion_renueva_un_precio_vencido_y_suma_confianza(
    reportante, vecina, django_user_model, arroz, tiendas, django_capture_on_commit_callbacks
):
    producto, p500, _ = arroz
    rosa, _ = tiendas
    viejo = services.cargar_reporte_historico(
        autor=reportante,
        presentacion_id=p500.pk,
        establecimiento_id=rosa.pk,
        precio=Decimal(2500),
        fecha_observacion=timezone.now() - timedelta(days=8),  # fuera de la ventana de 7 días
    )
    assert comparar_producto(producto.pk) == []

    with django_capture_on_commit_callbacks(execute=True):  # invalida la caché (ADR-0002)
        services.confirmar_precio(usuario=vecina, reporte_id=viejo.pk)
    resultados = comparar_producto(producto.pk)
    assert [r.establecimiento for r in resultados] == ["Tienda Doña Rosa"]  # EC-02 renovado
    assert resultados[0].confianza == "media"

    tercero = django_user_model.objects.create_user(username="tercero", password="x-clave-1234")
    with django_capture_on_commit_callbacks(execute=True):
        services.confirmar_precio(usuario=tercero, reporte_id=viejo.pk)
    assert comparar_producto(producto.pk)[0].confianza == "alta"  # 2 confirmaciones


def test_respeta_el_limite_de_confirmaciones_por_hora(settings, vecina, reporte, arroz, tiendas):
    settings.PRECIOS = {**settings.PRECIOS, "LIMITE_REPORTES_HORA": 1}
    _, _, p1kg = arroz
    _, super_ = tiendas
    otro = services.cargar_reporte_historico(  # sin RN-10: el límite de prueba es 1
        autor=reporte.autor,
        presentacion_id=p1kg.pk,
        establecimiento_id=super_.pk,
        precio=Decimal(4900),
        fecha_observacion=timezone.now(),
    )
    services.confirmar_precio(usuario=vecina, reporte_id=reporte.pk)
    services.confirmar_precio(usuario=vecina, reporte_id=reporte.pk)  # idempotente: no cuenta
    with pytest.raises(services.LimiteDeConfirmacionesExcedidoError):
        services.confirmar_precio(usuario=vecina, reporte_id=otro.pk)
