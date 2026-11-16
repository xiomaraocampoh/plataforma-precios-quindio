"""RF-08, RF-09, RF-10: directorio con filtros, enlace al mapa y sugerencias moderadas."""

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.comparacion.selectors import comparar_producto
from apps.establecimientos import services
from apps.establecimientos.models import Establecimiento
from apps.precios import services as precios
from apps.precios.forms import RegistroPrecioForm

pytestmark = pytest.mark.integration

SUGERENCIA = {
    "nombre": "Tienda Nueva",
    "tipo": "tienda",
    "direccion": "Cl 50 # 20-10",
    "barrio": "La Patria",
    "municipio": "Armenia",
}


@pytest.fixture
def calarca(db):
    return Establecimiento.objects.create(
        nombre="Mini Calarcá",
        tipo="minimercado",
        direccion="Cra 25 # 40-10",
        barrio="Centro",
        municipio="Calarcá",
    )


def test_directorio_filtra_por_municipio_barrio_y_tipo(client, tiendas, calarca):
    html = client.get(reverse("establecimientos:directorio"), {"municipio": "Calarcá"}).content
    assert "Mini Calarcá" in html.decode() and "Tienda Doña Rosa" not in html.decode()
    html = client.get(reverse("establecimientos:directorio"), {"tipo": "supermercado"}).content
    assert "Súper Quindío" in html.decode() and "Tienda Doña Rosa" not in html.decode()
    r = client.get(
        reverse("establecimientos:directorio"), {"barrio": "Centro"}, HTTP_HX_REQUEST="true"
    )
    assert "<html" not in r.content.decode()  # fragmento HTMX


def test_directorio_enlaza_al_mapa_solo_con_coordenadas(client, tiendas, calarca):
    html = client.get(reverse("establecimientos:directorio")).content.decode()
    assert "https://www.openstreetmap.org/?mlat=4.533889&amp;mlon=-75.681111" in html
    assert 'rel="noopener noreferrer"' in html
    assert "Sin ubicación en el mapa" in html  # Mini Calarcá no tiene coordenadas


def test_sugerir_exige_sesion(client, db):
    assert client.get(reverse("establecimientos:sugerir")).status_code == 302


def test_la_sugerencia_queda_pendiente_y_fuera_de_comparacion_y_registro(
    client, reportante, arroz, tiendas
):
    client.force_login(reportante)
    r = client.post(reverse("establecimientos:sugerir"), SUGERENCIA)
    assert r.status_code == 302
    nueva = Establecimiento.objects.get(nombre="Tienda Nueva")
    assert nueva.estado == Establecimiento.Estado.PENDIENTE and not nueva.activo
    assert nueva.sugerido_por == reportante
    html = client.get(reverse("establecimientos:directorio")).content.decode()
    assert "Tienda Nueva" not in html
    assert nueva not in RegistroPrecioForm().fields["establecimiento"].queryset
    _, p500, _ = arroz
    with pytest.raises(Exception, match="no existe o está inactivo"):
        precios.registrar_reporte(
            autor=reportante,
            presentacion_id=p500.pk,
            establecimiento_id=nueva.pk,
            precio=Decimal(2500),
        )


def test_al_aprobarse_entra_al_directorio_y_a_la_comparacion(
    reportante, arroz, tiendas, django_user_model
):
    moderador = django_user_model.objects.create_user(username="mod", password="x-clave-1234")
    nueva = services.sugerir_establecimiento(autor=reportante, **SUGERENCIA)
    services.aprobar_establecimiento(establecimiento_id=nueva.pk, moderador=moderador)
    nueva.refresh_from_db()
    assert nueva.activo and nueva.revisado_por == moderador and nueva.revisado_en
    producto, p500, _ = arroz
    precios.registrar_reporte(
        autor=reportante, presentacion_id=p500.pk, establecimiento_id=nueva.pk, precio=Decimal(2500)
    )
    assert [r.establecimiento for r in comparar_producto(producto.pk)] == ["Tienda Nueva"]


def test_coordenadas_incompletas_se_rechazan(client, reportante):
    client.force_login(reportante)
    html = client.post(
        reverse("establecimientos:sugerir"), {**SUGERENCIA, "latitud": "4.5"}
    ).content.decode()
    assert "Escribe la latitud y la longitud juntas" in html


def test_api_lista_establecimientos_sin_datos_del_sugerente(api, tiendas, calarca, reportante):
    services.sugerir_establecimiento(autor=reportante, **SUGERENCIA)  # pendiente: no se lista
    r = api.get(reverse("api-establecimientos"), {"municipio": "Armenia"})
    assert r.status_code == 200
    nombres = {e["nombre"] for e in r.json()["results"]}
    assert nombres == {"Tienda Doña Rosa", "Súper Quindío"}
    item = r.json()["results"][0]
    assert "sugerido_por" not in item and "revisado_por" not in item  # EC-07
    assert item["enlace_mapa"].startswith("https://www.openstreetmap.org/")


def test_api_sugerencia_exige_autenticacion_y_queda_pendiente(api, reportante):
    assert api.post(reverse("api-sugerencias"), SUGERENCIA).status_code == 403
    api.force_authenticate(reportante)
    r = api.post(reverse("api-sugerencias"), SUGERENCIA)
    assert r.status_code == 201
    assert r.json()["estado"] == "pendiente"
