"""Permisos del panel verificados en el servidor, por rol (no basta con ocultar botones)."""

import pytest
from django.urls import reverse

from apps.administracion.models import RegistroAuditoria
from apps.catalogo.models import Marca

pytestmark = pytest.mark.integration

SECCIONES = ["marcas", "categorias", "productos", "establecimientos"]


def _rutas_get(datos, usuario_objetivo):
    objetos = {
        "marcas": datos["diana"].pk,
        "categorias": datos["granos"].pk,
        "productos": datos["arroz"].pk,
        "establecimientos": datos["tienda"].pk,
    }
    rutas = [reverse("panel:inicio"), reverse("panel:usuarios"), reverse("panel:auditoria")]
    rutas.append(reverse("panel:usuario", args=[usuario_objetivo.pk]))
    rutas.append(reverse("panel:usuario_estado", args=[usuario_objetivo.pk]))
    for seccion, pk in objetos.items():
        rutas += [
            reverse("panel:lista", args=[seccion]),
            reverse("panel:nuevo", args=[seccion]),
            reverse("panel:editar", args=[seccion, pk]),
            reverse("panel:estado", args=[seccion, pk]),
            reverse("panel:eliminar", args=[seccion, pk]),
        ]
    return rutas


def _rutas_post(datos, usuario_objetivo):
    return [
        (reverse("panel:nuevo", args=["marcas"]), {"nombre": "Roa"}),
        (reverse("panel:editar", args=["marcas", datos["diana"].pk]), {"nombre": "Otra"}),
        (reverse("panel:estado", args=["marcas", datos["diana"].pk]), {}),
        (reverse("panel:eliminar", args=["categorias", datos["granos"].pk]), {}),
        (reverse("panel:estado", args=["establecimientos", datos["tienda"].pk]), {}),
        (reverse("panel:usuario", args=[usuario_objetivo.pk]), {"rol": "administrador"}),
        (reverse("panel:usuario_estado", args=[usuario_objetivo.pk]), {}),
    ]


def test_sin_sesion_el_panel_pide_ingresar(client, db):
    r = client.get(reverse("panel:inicio"))
    assert r.status_code == 302 and reverse("cuentas:ingresar") in r["Location"]


def test_el_reportante_recibe_403_en_todas_las_vistas_del_panel(entrar, datos, crear_usuario):
    objetivo = crear_usuario("reportante", username="vecina")
    client, _ = entrar("reportante")
    for ruta in _rutas_get(datos, objetivo):
        assert client.get(ruta).status_code == 403, ruta
    for ruta, cuerpo in _rutas_post(datos, objetivo):
        assert client.post(ruta, cuerpo).status_code == 403, ruta
    # Nada cambió: el 403 llega antes de cualquier escritura
    assert set(Marca.objects.values_list("nombre", "activa")) == {("Diana", True)}
    objetivo.refresh_from_db()
    assert objetivo.rol == "reportante" and objetivo.is_active
    assert not RegistroAuditoria.objects.exists()


def test_el_reportante_no_ve_el_enlace_al_panel(entrar, db):
    client, _ = entrar("reportante")
    assert reverse("panel:inicio") not in client.get(reverse("comparacion:inicio")).content.decode()


def test_el_editor_de_catalogo_solo_entra_al_catalogo(entrar, datos, crear_usuario):
    objetivo = crear_usuario("reportante", username="vecina")
    client, _ = entrar("editor_catalogo")
    assert reverse("panel:inicio") in client.get(reverse("comparacion:inicio")).content.decode()
    for seccion in ["marcas", "categorias", "productos"]:
        assert client.get(reverse("panel:lista", args=[seccion])).status_code == 200
        assert client.get(reverse("panel:nuevo", args=[seccion])).status_code == 200
    for ruta in [
        reverse("panel:lista", args=["establecimientos"]),
        reverse("panel:usuarios"),
        reverse("panel:usuario", args=[objetivo.pk]),
        reverse("panel:auditoria"),
    ]:
        assert client.get(ruta).status_code == 403, ruta
    assert (
        client.post(reverse("panel:nuevo", args=["marcas"]), {"nombre": "Roa"}).status_code == 302
    )
    assert Marca.objects.filter(nombre="Roa").exists()


def test_el_moderador_consulta_pero_no_edita_el_catalogo(entrar, datos, crear_usuario):
    objetivo = crear_usuario("reportante", username="vecina")
    client, _ = entrar("moderador")
    assert client.get(reverse("panel:lista", args=["productos"])).status_code == 200
    assert client.get(reverse("panel:nuevo", args=["productos"])).status_code == 403
    assert client.post(reverse("panel:nuevo", args=["marcas"]), {"nombre": "X"}).status_code == 403
    assert client.get(reverse("panel:usuarios")).status_code == 200  # ver, sí
    r = client.post(reverse("panel:usuario", args=[objetivo.pk]), {"rol": "administrador"})
    assert r.status_code == 403  # asignar roles, no
    assert client.get(reverse("panel:auditoria")).status_code == 403


@pytest.mark.parametrize("rol", ["administrador", "superusuario"])
def test_administracion_entra_a_todo(entrar, datos, crear_usuario, rol):
    objetivo = crear_usuario("reportante", username="vecina")
    if rol == "superusuario":
        client, _ = entrar("reportante", is_superuser=True)
    else:
        client, _ = entrar(rol)
    for ruta in _rutas_get(datos, objetivo):
        assert client.get(ruta).status_code == 200, ruta


def test_una_seccion_inexistente_es_404(entrar, db):
    client, _ = entrar("administrador")
    assert client.get("/panel/comercios/").status_code == 404
