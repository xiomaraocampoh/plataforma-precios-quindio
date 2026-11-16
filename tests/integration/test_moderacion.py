"""RF-20 denuncias, RF-21 bandeja y decisiones, RF-22 suspensión (moderador y fecha)."""

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.catalogo import services as catalogo
from apps.comparacion.selectors import comparar_producto
from apps.cuentas.models import Usuario
from apps.establecimientos import services as establecimientos
from apps.moderacion import services
from apps.moderacion.models import DecisionModeracion, Denuncia
from apps.precios import services as precios
from apps.precios.models import ReportePrecio

pytestmark = pytest.mark.integration


@pytest.fixture
def moderador(django_user_model):
    return django_user_model.objects.create_user(
        username="moderadora", password="x-clave-segura-1", rol=Usuario.Rol.MODERADOR
    )


@pytest.fixture
def vecina(django_user_model):
    return django_user_model.objects.create_user(username="vecina", password="x-clave-segura-1")


@pytest.fixture
def reporte(reportante, arroz, tiendas):
    _, p500, _ = arroz
    rosa, _ = tiendas
    return precios.registrar_reporte(
        autor=reportante, presentacion_id=p500.pk, establecimiento_id=rosa.pk, precio=Decimal(2500)
    )


# ---------- RF-20: denunciar ----------


def test_denunciar_desde_la_comparacion_una_sola_vez(client, vecina, reporte, arroz):
    producto, _, _ = arroz
    client.force_login(vecina)
    url = reverse("moderacion:denunciar", args=[reporte.pk])
    assert (
        "Denunciar"
        in client.get(reverse("comparacion:comparar", args=[producto.pk])).content.decode()
    )
    formulario = client.get(url, HTTP_HX_REQUEST="true").content.decode()
    assert f'for="denuncia-{reporte.pk}-motivo"' in formulario  # etiqueta con id único
    datos = {"motivo": "precio_falso", "detalle": "Lo vi a 2.900"}
    primera = client.post(url, datos, HTTP_HX_REQUEST="true").content.decode()
    segunda = client.post(url, datos, HTTP_HX_REQUEST="true").content.decode()
    assert "Gracias. Moderación revisará este precio." in primera
    assert "Ya denunciaste este precio." in segunda
    assert Denuncia.objects.filter(reporte=reporte, denunciante=vecina).count() == 1
    html = client.get(reverse("comparacion:comparar", args=[producto.pk])).content.decode()
    assert "Ya denunciaste este precio; moderación lo revisará." in html


def test_denunciar_exige_sesion(client, reporte):
    assert client.post(reverse("moderacion:denunciar", args=[reporte.pk])).status_code == 302


def test_no_se_denuncia_un_precio_propio(reportante, reporte):
    with pytest.raises(Exception, match="reportaste tú"):
        services.denunciar(denunciante=reportante, reporte_id=reporte.pk, motivo="otro")


# ---------- RF-21: bandeja y permisos ----------


def test_la_bandeja_es_solo_para_moderacion(client, vecina, moderador, db):
    assert client.get(reverse("moderacion:bandeja")).status_code == 302  # anónimo: al ingreso
    client.force_login(vecina)
    assert client.get(reverse("moderacion:bandeja")).status_code == 403
    client.force_login(moderador)
    assert client.get(reverse("moderacion:bandeja")).status_code == 200


def test_el_personal_staff_tambien_modera(client, django_user_model, db):
    staff = django_user_model.objects.create_user(
        username="staff", password="x-clave-1234", is_staff=True
    )
    client.force_login(staff)
    assert client.get(reverse("moderacion:bandeja")).status_code == 200


def test_la_bandeja_muestra_todo_lo_pendiente(
    client, moderador, vecina, reportante, reporte, arroz, tiendas
):
    ReportePrecio.objects.filter(pk=reporte.pk).update(estado=ReportePrecio.Estado.EN_REVISION)
    otro = precios.registrar_reporte(
        autor=reportante,
        presentacion_id=arroz[2].pk,
        establecimiento_id=tiendas[1].pk,
        precio=Decimal(4900),
    )
    services.denunciar(denunciante=vecina, reporte_id=otro.pk, motivo="producto")
    catalogo.solicitar_producto(
        solicitante=vecina,
        nombre="Lentejas",
        marca="",
        categoria_id=arroz[0].categoria_id,
        cantidad=Decimal(500),
        unidad="g",
    )
    establecimientos.sugerir_establecimiento(
        autor=vecina, nombre="Tienda Nueva", tipo="tienda", direccion="Cl 1"
    )
    client.force_login(moderador)
    html = client.get(reverse("moderacion:bandeja")).content.decode()
    for texto in [
        "En revisión (1)",
        "Denuncias (1)",
        "Productos (1)",
        "Establecimientos (1)",
        "Producto o presentación equivocada",
        "Lentejas",
        "Tienda Nueva",
    ]:
        assert texto in html


# ---------- Decisiones ----------


def _decidir(client, tipo, objeto_id, decision="aprobar", motivo=""):
    datos = {"tipo": tipo, "objeto_id": objeto_id, "decision": decision, "motivo": motivo}
    return client.post(reverse("moderacion:decidir"), datos, HTTP_HX_REQUEST="true")


def test_publicar_un_reporte_en_revision_lo_lleva_a_la_comparacion(
    client, moderador, reporte, arroz, django_capture_on_commit_callbacks
):
    producto, _, _ = arroz
    ReportePrecio.objects.filter(pk=reporte.pk).update(estado=ReportePrecio.Estado.EN_REVISION)
    client.force_login(moderador)
    with django_capture_on_commit_callbacks(execute=True):
        r = _decidir(client, "reporte", reporte.pk, motivo="Precio verificado")
    assert "Decisión registrada." in r.content.decode()
    reporte.refresh_from_db()
    assert reporte.estado == ReportePrecio.Estado.PUBLICADO
    decision = DecisionModeracion.objects.get()
    assert decision.moderador == moderador and decision.creado_en is not None
    assert decision.accion == "aprobar_reporte" and decision.motivo == "Precio verificado"
    assert len(comparar_producto(producto.pk)) == 1


def test_aceptar_una_denuncia_retira_el_precio(
    client, moderador, vecina, reporte, arroz, django_capture_on_commit_callbacks
):
    producto, _, _ = arroz
    denuncia = services.denunciar(denunciante=vecina, reporte_id=reporte.pk, motivo="precio_falso")
    client.force_login(moderador)
    with django_capture_on_commit_callbacks(execute=True):
        _decidir(client, "denuncia", denuncia.pk, "aprobar")
    denuncia.refresh_from_db()
    assert denuncia.estado == Denuncia.Estado.ACEPTADA
    assert denuncia.resuelto_por == moderador and denuncia.resuelto_en
    assert comparar_producto(producto.pk) == []


def test_descartar_una_denuncia_conserva_el_precio(client, moderador, vecina, reporte, arroz):
    denuncia = services.denunciar(denunciante=vecina, reporte_id=reporte.pk, motivo="otro")
    client.force_login(moderador)
    _decidir(client, "denuncia", denuncia.pk, "rechazar")
    denuncia.refresh_from_db()
    reporte.refresh_from_db()
    assert denuncia.estado == Denuncia.Estado.DESCARTADA
    assert reporte.estado == ReportePrecio.Estado.PUBLICADO


def test_suspender_la_cuenta_registra_la_decision(client, moderador, reportante, reporte):
    client.force_login(moderador)
    _decidir(client, "usuario", reportante.pk, motivo="Reportes falsos repetidos")
    reportante.refresh_from_db()
    assert not reportante.is_active
    assert DecisionModeracion.objects.get().accion == "suspender_cuenta"
    assert ReportePrecio.objects.filter(autor=reportante).exists()  # aportes auditables


def test_no_se_suspende_a_personal_ni_a_si_mismo(client, moderador, django_user_model, db):
    staff = django_user_model.objects.create_user(
        username="staff", password="x-clave-1234", is_staff=True
    )
    client.force_login(moderador)
    assert "No se puede suspender" in _decidir(client, "usuario", staff.pk).content.decode()
    assert "tu propia cuenta" in _decidir(client, "usuario", moderador.pk).content.decode()
    assert DecisionModeracion.objects.count() == 0


def test_un_usuario_comun_no_puede_decidir(client, vecina, reporte):
    client.force_login(vecina)
    assert _decidir(client, "reporte", reporte.pk).status_code == 403


def test_aprobar_solicitud_y_establecimiento_desde_la_bandeja(client, moderador, vecina, arroz):
    solicitud = catalogo.solicitar_producto(
        solicitante=vecina,
        nombre="Lentejas",
        marca="",
        categoria_id=arroz[0].categoria_id,
        cantidad=Decimal(500),
        unidad="g",
    )
    nueva = establecimientos.sugerir_establecimiento(
        autor=vecina, nombre="Tienda Nueva", tipo="tienda", direccion="Cl 1"
    )
    client.force_login(moderador)
    _decidir(client, "solicitud", solicitud.pk)
    _decidir(client, "establecimiento", nueva.pk, "rechazar")
    solicitud.refresh_from_db()
    nueva.refresh_from_db()
    assert solicitud.estado == "aprobada" and solicitud.presentacion_creada is not None
    assert nueva.estado == "rechazado" and not nueva.activo
    assert DecisionModeracion.objects.count() == 2


# ---------- API v1 ----------


def test_api_denuncias(api, vecina, reportante, reporte):
    url = reverse("api-denuncias")
    datos = {"reporte": reporte.pk, "motivo": "precio_falso"}
    assert api.post(url, datos).status_code == 403  # sin sesión
    api.force_authenticate(vecina)
    r = api.post(url, datos)
    assert r.status_code == 201 and r.json()["estado"] == "abierta"
    assert api.post(url, datos).status_code == 409  # una sola por usuario y reporte
    assert api.post(url, {"reporte": 99999, "motivo": "otro"}).status_code == 400


def test_api_reportes_en_revision_solo_moderacion_y_sin_autor(api, moderador, vecina, reporte):
    ReportePrecio.objects.filter(pk=reporte.pk).update(estado=ReportePrecio.Estado.EN_REVISION)
    url = reverse("api-en-revision")
    api.force_authenticate(vecina)
    assert api.get(url).status_code == 403
    api.force_authenticate(moderador)
    r = api.get(url)
    assert r.status_code == 200
    item = r.json()["results"][0]
    assert item["id"] == reporte.pk
    assert "autor" not in item  # EC-07: ni siquiera para moderación por API
    detalle = reverse("api-en-revision-detalle", args=[reporte.pk])
    r = api.patch(detalle, {"decision": "rechazar", "motivo": "Duplicado"}, format="json")
    assert r.status_code == 200 and r.json()["estado"] == "rechazado"
    assert api.get(detalle).status_code == 404  # ya no está en revisión
    assert DecisionModeracion.objects.get().moderador == moderador
