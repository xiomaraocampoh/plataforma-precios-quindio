"""Punto 13 y RF-21/22 en /admin/: filtros del catálogo y acciones de moderación registradas."""

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.catalogo import services as catalogo
from apps.catalogo.models import Categoria, Presentacion, Producto
from apps.moderacion.models import DecisionModeracion

pytestmark = pytest.mark.integration


@pytest.fixture
def admin_client_(client, django_user_model):
    admin = django_user_model.objects.create_superuser(username="adm", password="x-clave-1234")
    client.force_login(admin)
    return client, admin


@pytest.mark.parametrize(
    "modelo",
    [
        "catalogo_producto",
        "catalogo_presentacion",
        "catalogo_solicitudcatalogo",
        "precios_reporteprecio",
        "precios_confirmacionprecio",
        "moderacion_denuncia",
        "moderacion_decisionmoderacion",
        "establecimientos_establecimiento",
        "integraciones_precioreferencia",
        "cuentas_usuario",
    ],
)
def test_las_listas_del_admin_cargan(admin_client_, modelo):
    client, _ = admin_client_
    assert client.get(reverse(f"admin:{modelo}_changelist")).status_code == 200


def test_presentacion_se_busca_por_codigo_y_filtra_por_marca(admin_client_, arroz):
    client, _ = admin_client_
    _, p500, _ = arroz
    Presentacion.objects.filter(pk=p500.pk).update(codigo_barras="7702001001234")
    otra = Categoria.objects.create(nombre="Abarrotes")  # con 2 valores el filtro se muestra
    cafe = Producto.objects.create(
        nombre="Café", marca="Águila Roja", nombre_normalizado="cafe", categoria=otra
    )
    Presentacion.objects.create(producto=cafe, cantidad=Decimal(250), unidad="g")
    url = reverse("admin:catalogo_presentacion_changelist")
    assert "Arroz blanco 500 g" in client.get(url, {"q": "7702001001234"}).content.decode()
    html = client.get(url).content.decode()
    assert "producto__marca" in html and "producto__categoria__id__exact" in html


def test_accion_de_admin_aprueba_y_registra_la_decision(admin_client_, reportante, arroz):
    client, admin = admin_client_
    solicitud = catalogo.solicitar_producto(
        solicitante=reportante,
        nombre="Lentejas",
        marca="",
        categoria_id=arroz[0].categoria_id,
        cantidad=Decimal(500),
        unidad="g",
    )
    r = client.post(
        reverse("admin:catalogo_solicitudcatalogo_changelist"),
        {"action": "accion_aprobar_y_agregar_al_catalogo", "_selected_action": [solicitud.pk]},
        follow=True,
    )
    assert r.status_code == 200
    solicitud.refresh_from_db()
    assert solicitud.estado == "aprobada"
    decision = DecisionModeracion.objects.get()
    assert decision.moderador == admin and decision.accion == "aprobar_solicitud"


def test_la_bitacora_de_decisiones_no_se_edita(admin_client_):
    client, _ = admin_client_
    assert client.get(reverse("admin:moderacion_decisionmoderacion_add")).status_code == 403
