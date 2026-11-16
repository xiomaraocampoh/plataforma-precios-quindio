"""Roles y permisos de la plataforma (dominio puro; se aplican con Groups de Django)."""

import pytest

from apps.cuentas.domain.roles import (
    GRUPOS,
    PERMISOS,
    CambioDeCuentaNoPermitidoError,
    Rol,
    grupo_de,
    validar_cambio_de_cuenta,
)

pytestmark = pytest.mark.unit


def test_cada_rol_asignable_tiene_su_grupo():
    assert GRUPOS == {
        Rol.ADMINISTRADOR: "Administrador",
        Rol.MODERADOR: "Moderador",
        Rol.EDITOR_CATALOGO: "Editor de catálogo",
        Rol.REPORTANTE: "Reportante",
    }
    assert grupo_de("comercio") is None  # Corte III: sin grupo todavía
    assert grupo_de("desconocido") is None


def test_el_reportante_no_tiene_permisos_del_panel():
    assert not any(
        p.split(".")[1].startswith(("change_", "delete_")) for p in PERMISOS[Rol.REPORTANTE]
    )
    assert "catalogo.add_marca" not in PERMISOS[Rol.REPORTANTE]


def test_el_editor_gestiona_solo_el_catalogo():
    apps = {p.split(".")[0] for p in PERMISOS[Rol.EDITOR_CATALOGO]}
    assert apps == {"catalogo"}
    assert {"catalogo.add_marca", "catalogo.change_producto", "catalogo.delete_categoria"} <= (
        PERMISOS[Rol.EDITOR_CATALOGO]
    )


def test_el_administrador_reune_catalogo_establecimientos_cuentas_y_auditoria():
    admin = PERMISOS[Rol.ADMINISTRADOR]
    assert PERMISOS[Rol.EDITOR_CATALOGO] <= admin
    assert PERMISOS[Rol.MODERADOR] <= admin
    assert {
        "establecimientos.change_establecimiento",
        "cuentas.gestionar_cuentas",
        "administracion.view_registroauditoria",
    } <= admin
    assert "cuentas.gestionar_cuentas" not in PERMISOS[Rol.MODERADOR]


def test_nadie_cambia_su_propia_cuenta():
    with pytest.raises(CambioDeCuentaNoPermitidoError, match="propi"):
        validar_cambio_de_cuenta(
            actor_id=1, objetivo_id=1, actor_es_superusuario=True, objetivo_es_superusuario=True
        )


def test_solo_un_superusuario_cambia_a_otro_superusuario():
    with pytest.raises(CambioDeCuentaNoPermitidoError, match="superusuario"):
        validar_cambio_de_cuenta(
            actor_id=1, objetivo_id=2, actor_es_superusuario=False, objetivo_es_superusuario=True
        )
    validar_cambio_de_cuenta(
        actor_id=1, objetivo_id=2, actor_es_superusuario=True, objetivo_es_superusuario=True
    )
    validar_cambio_de_cuenta(
        actor_id=1, objetivo_id=2, actor_es_superusuario=False, objetivo_es_superusuario=False
    )
