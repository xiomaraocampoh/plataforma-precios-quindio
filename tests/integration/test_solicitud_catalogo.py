"""RF-06 + PU-05: solicitud de producto con aviso de posibles duplicados (D-05)."""

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.catalogo import services
from apps.catalogo.domain.duplicados import normalizar_nombre
from apps.catalogo.models import Categoria, Presentacion, Producto, SolicitudCatalogo

pytestmark = pytest.mark.integration


@pytest.fixture
def aceite(db):
    abarrotes = Categoria.objects.create(nombre="Abarrotes")
    producto = Producto.objects.create(
        nombre="Aceite",
        marca="Premier",
        nombre_normalizado=normalizar_nombre("Aceite"),
        categoria=abarrotes,
    )
    Presentacion.objects.create(producto=producto, cantidad=Decimal(1), unidad="L")
    return producto


def _datos(categoria, **extra):
    datos = {"nombre": "Aceite", "marca": "Premier", "categoria": categoria.pk}
    datos.update({"cantidad": "3", "unidad": "L", "codigo_barras": "", "detalle": ""})
    datos.update(extra)
    return datos


def test_exige_sesion(client, db):
    assert client.get(reverse("catalogo:solicitar")).status_code == 302


def test_muestra_productos_similares_mientras_se_escribe(client, aceite):
    # «Aceite Premir» (error de digitación) se parece ≥ 0,85 a «Aceite Premier»
    html = client.get(
        reverse("catalogo:similares"), {"nombre": "Aceite", "marca": "Premir"}
    ).content.decode()
    assert "¿Es alguno de estos?" in html
    assert "Aceite Premier" in html


def test_nombres_distintos_no_se_muestran_como_similares(client, aceite):
    html = client.get(reverse("catalogo:similares"), {"nombre": "Leche entera"}).content.decode()
    assert "Aceite" not in html


def test_la_solicitud_queda_pendiente_y_no_entra_al_catalogo(client, reportante, aceite):
    client.force_login(reportante)
    r = client.post(reverse("catalogo:solicitar"), _datos(aceite.categoria))
    assert r.status_code == 302
    solicitud = SolicitudCatalogo.objects.get()
    assert solicitud.estado == SolicitudCatalogo.Estado.PENDIENTE
    assert solicitud.solicitante == reportante
    assert not Presentacion.objects.filter(producto=aceite, cantidad=3).exists()


def test_una_presentacion_existente_se_rechaza(client, reportante, aceite):
    client.force_login(reportante)
    html = client.post(
        reverse("catalogo:solicitar"), _datos(aceite.categoria, cantidad="1")
    ).content.decode()
    assert "Esa presentación ya está en el catálogo." in html
    assert SolicitudCatalogo.objects.count() == 0


def test_codigo_de_barras_invalido(client, reportante, aceite):
    client.force_login(reportante)
    html = client.post(
        reverse("catalogo:solicitar"), _datos(aceite.categoria, codigo_barras="12ab")
    ).content.decode()
    assert 'id="id_codigo_barras_error"' in html


def test_aprobar_crea_la_presentacion_y_registra_al_moderador(
    reportante, aceite, django_user_model
):
    moderador = django_user_model.objects.create_user(username="mod", password="x-clave-1234")
    solicitud = services.solicitar_producto(
        solicitante=reportante,
        nombre="Aceite",
        marca="Premier",
        categoria_id=aceite.categoria_id,
        cantidad=Decimal(3),
        unidad="L",
    )
    services.aprobar_solicitud(solicitud_id=solicitud.pk, moderador=moderador)
    solicitud.refresh_from_db()
    assert solicitud.estado == SolicitudCatalogo.Estado.APROBADA
    assert solicitud.resuelto_por == moderador and solicitud.resuelto_en is not None
    assert solicitud.presentacion_creada.producto == aceite  # reutiliza el producto existente
    with pytest.raises(ValueError):
        services.rechazar_solicitud(solicitud_id=solicitud.pk, moderador=moderador)
