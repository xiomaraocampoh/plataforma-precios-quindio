"""Establecimientos, usuarios y auditoría en el panel."""

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.administracion.models import RegistroAuditoria
from apps.establecimientos.models import Establecimiento
from apps.precios import services as precios

from .conftest import controles_sin_etiqueta, referencias_rotas

pytestmark = pytest.mark.integration

NUEVA_TIENDA = {
    "nombre": "Tienda La Esquina",
    "tipo": "tienda",
    "direccion": "Cl 10 # 5-20",
    "barrio": "Centro",
    "municipio": "Armenia",
    "latitud": "",
    "longitud": "",
}

# ---------- Establecimientos ----------


def test_crear_y_editar_un_establecimiento(entrar, db):
    client, _ = entrar("administrador")
    assert (
        client.post(reverse("panel:nuevo", args=["establecimientos"]), NUEVA_TIENDA).status_code
        == 302
    )
    tienda = Establecimiento.objects.get(nombre="Tienda La Esquina")
    assert tienda.activo and tienda.estado == "aprobado"
    client.post(
        reverse("panel:editar", args=["establecimientos", tienda.pk]),
        {**NUEVA_TIENDA, "barrio": "Granada"},
    )
    tienda.refresh_from_db()
    assert tienda.barrio == "Granada"
    assert list(RegistroAuditoria.objects.order_by("pk").values_list("accion", flat=True)) == [
        "crear",
        "editar",
    ]


def test_coordenadas_incompletas_se_rechazan(entrar, db):
    client, _ = entrar("administrador")
    html = client.post(
        reverse("panel:nuevo", args=["establecimientos"]), {**NUEVA_TIENDA, "latitud": "4.53"}
    ).content.decode()
    assert "latitud y la longitud" in html
    assert not Establecimiento.objects.exists()


def test_un_establecimiento_con_reportes_no_se_elimina(entrar, datos, reportante):
    precios.registrar_reporte(
        autor=reportante,
        presentacion_id=datos["p500"].pk,
        establecimiento_id=datos["tienda"].pk,
        precio=Decimal(2600),
    )
    client, _ = entrar("administrador")
    client.post(reverse("panel:eliminar", args=["establecimientos", datos["tienda"].pk]))
    assert Establecimiento.objects.filter(pk=datos["tienda"].pk).exists()


def test_un_establecimiento_pendiente_no_se_activa_desde_el_panel(entrar, db, reportante):
    pendiente = Establecimiento.objects.create(
        nombre="Sugerida", tipo="tienda", direccion="Cl 1", estado="pendiente", activo=False
    )
    client, _ = entrar("administrador")
    r = client.post(reverse("panel:estado", args=["establecimientos", pendiente.pk]), follow=True)
    pendiente.refresh_from_db()
    assert not pendiente.activo
    assert "moderación" in r.content.decode()


def test_filtros_de_establecimientos(entrar, datos):
    Establecimiento.objects.create(
        nombre="Súper Quindío", tipo="supermercado", direccion="Av. Bolívar", municipio="Calarcá"
    )
    client, _ = entrar("administrador")
    url = reverse("panel:lista", args=["establecimientos"])
    html = client.get(url, {"tipo": "supermercado"}).content.decode()
    assert "Súper Quindío" in html and "Tienda Doña Rosa" not in html
    html = client.get(url, {"municipio": "Armenia"}).content.decode()
    assert "Tienda Doña Rosa" in html and "Súper Quindío" not in html


# ---------- Usuarios ----------


def test_el_administrador_asigna_un_rol_y_queda_auditado(entrar, crear_usuario):
    vecina = crear_usuario("reportante", username="vecina")
    client, admin = entrar("administrador")
    r = client.post(reverse("panel:usuario", args=[vecina.pk]), {"rol": "editor_catalogo"})
    assert r.status_code == 302
    vecina.refresh_from_db()
    assert vecina.rol == "editor_catalogo"
    assert set(vecina.groups.values_list("name", flat=True)) == {"Editor de catálogo"}
    registro = RegistroAuditoria.objects.get()
    assert (registro.actor, registro.accion, registro.entidad) == (admin, "asignar_rol", "usuario")
    assert registro.cambios == {"rol": ["reportante", "editor_catalogo"]}


def test_el_administrador_no_cambia_su_propia_cuenta(entrar):
    client, admin = entrar("administrador")
    html = client.get(reverse("panel:usuario", args=[admin.pk])).content.decode()
    assert "No puedes cambiar tu propio rol" in html  # se explica en vez de mostrar el formulario
    r = client.post(reverse("panel:usuario", args=[admin.pk]), {"rol": "reportante"})
    assert r.status_code == 200 and "propi" in r.content.decode()
    client.post(reverse("panel:usuario_estado", args=[admin.pk]))
    admin.refresh_from_db()
    assert admin.rol == "administrador" and admin.is_active
    assert not RegistroAuditoria.objects.exists()


def test_suspender_y_reactivar_con_confirmacion(entrar, crear_usuario):
    vecina = crear_usuario("reportante", username="vecina")
    client, _ = entrar("administrador")
    url = reverse("panel:usuario_estado", args=[vecina.pk])
    assert "¿Suspender la cuenta «vecina»?" in client.get(url).content.decode()
    client.post(url)
    vecina.refresh_from_db()
    assert not vecina.is_active
    client.post(url)
    vecina.refresh_from_db()
    assert vecina.is_active
    acciones = list(RegistroAuditoria.objects.order_by("pk").values_list("accion", "cambios"))
    assert acciones == [
        ("desactivar", {"is_active": [True, False]}),
        ("activar", {"is_active": [False, True]}),
    ]


def test_un_administrador_no_suspende_a_un_superusuario(entrar, django_user_model):
    raiz = django_user_model.objects.create_superuser(username="raiz", password="x-clave-1234")
    client, _ = entrar("administrador")
    client.post(reverse("panel:usuario_estado", args=[raiz.pk]))
    raiz.refresh_from_db()
    assert raiz.is_active


def test_listado_de_usuarios_filtra_por_rol_y_estado(entrar, crear_usuario):
    crear_usuario("moderador", username="mod1")
    crear_usuario("reportante", username="vecina", is_active=False)
    client, _ = entrar("administrador")
    url = reverse("panel:usuarios")
    html = client.get(url, {"rol": "moderador"}).content.decode()
    assert "mod1" in html and "vecina" not in html
    html = client.get(url, {"activo": "no"}).content.decode()
    assert "vecina" in html and "mod1" not in html
    html = client.get(url, {"q": "VECI"}).content.decode()
    assert "vecina" in html
    assert controles_sin_etiqueta(html) == [] and referencias_rotas(html) == []


# ---------- Auditoría ----------


def test_la_bitacora_muestra_quien_que_y_cuando(entrar, datos):
    client, admin = entrar("administrador")
    client.post(reverse("panel:estado", args=["marcas", datos["diana"].pk]))
    html = client.get(reverse("panel:auditoria")).content.decode()
    assert admin.username in html and "Desactivar" in html and "Diana" in html
    assert "<time datetime=" in html
    filtrado = client.get(reverse("panel:auditoria"), {"entidad": "usuario"}).content.decode()
    assert "Diana" not in filtrado
    assert controles_sin_etiqueta(html) == [] and referencias_rotas(html) == []
