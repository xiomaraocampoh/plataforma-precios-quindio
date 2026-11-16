"""Roles con Groups y Permissions de Django, sincronizados con Usuario.rol."""

import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.cuentas import services
from apps.cuentas.domain.roles import GRUPOS, PERMISOS, Rol
from apps.cuentas.models import Usuario
from apps.moderacion.permisos import es_moderador

pytestmark = pytest.mark.integration


def _permisos(grupo: Group) -> set[str]:
    return {f"{p.content_type.app_label}.{p.codename}" for p in grupo.permissions.all()}


def _grupos_de_rol(usuario) -> set[str]:
    return set(usuario.groups.filter(name__in=GRUPOS.values()).values_list("name", flat=True))


@pytest.fixture
def administradora(django_user_model):
    return django_user_model.objects.create_user(
        username="adminpanel", password="x-clave-1234", rol=Rol.ADMINISTRADOR
    )


@pytest.mark.parametrize("rol", list(Rol))
def test_la_migracion_crea_los_grupos_con_sus_permisos(db, rol):
    assert _permisos(Group.objects.get(name=GRUPOS[rol])) == set(PERMISOS[rol])


def test_el_grupo_antiguo_de_moderadores_ya_no_existe(db):
    assert not Group.objects.filter(name="Moderadores").exists()


def test_quien_se_registra_queda_en_el_grupo_reportante(db):
    usuario = services.registrar_usuario(username="nueva", email="n@x.co", password="x-1234-abc")
    assert _grupos_de_rol(usuario) == {"Reportante"}
    assert usuario.has_perm("precios.add_reporteprecio")
    assert not usuario.has_perm("catalogo.add_marca")


def test_asignar_un_rol_cambia_el_grupo_y_los_permisos(administradora, reportante):
    services.asignar_rol(actor=administradora, usuario_id=reportante.pk, rol=Rol.EDITOR_CATALOGO)
    usuario = Usuario.objects.get(pk=reportante.pk)  # sin la caché de permisos
    assert usuario.rol == Rol.EDITOR_CATALOGO
    assert _grupos_de_rol(usuario) == {"Editor de catálogo"}
    assert usuario.has_perm("catalogo.add_marca")
    assert not usuario.has_perm("precios.add_reporteprecio")


def test_otros_grupos_que_no_son_de_rol_se_conservan(administradora, reportante):
    extra = Group.objects.create(name="Piloto Armenia")
    reportante.groups.add(extra)
    services.asignar_rol(actor=administradora, usuario_id=reportante.pk, rol=Rol.MODERADOR)
    assert set(reportante.groups.values_list("name", flat=True)) == {"Moderador", "Piloto Armenia"}


def test_nadie_cambia_su_propio_rol_ni_se_suspende(administradora):
    with pytest.raises(ValidationError, match="propi"):
        services.asignar_rol(actor=administradora, usuario_id=administradora.pk, rol=Rol.REPORTANTE)
    with pytest.raises(ValidationError, match="propi"):
        services.cambiar_estado_cuenta(
            actor=administradora, usuario_id=administradora.pk, activa=False
        )


def test_un_administrador_no_toca_a_un_superusuario(administradora, django_user_model):
    raiz = django_user_model.objects.create_superuser(username="raiz", password="x-clave-1234")
    with pytest.raises(ValidationError, match="superusuario"):
        services.cambiar_estado_cuenta(actor=administradora, usuario_id=raiz.pk, activa=False)


def test_suspender_y_reactivar_una_cuenta(administradora, reportante):
    services.cambiar_estado_cuenta(actor=administradora, usuario_id=reportante.pk, activa=False)
    reportante.refresh_from_db()
    assert not reportante.is_active
    services.cambiar_estado_cuenta(actor=administradora, usuario_id=reportante.pk, activa=True)
    reportante.refresh_from_db()
    assert reportante.is_active


def test_una_cuenta_suprimida_por_su_titular_no_se_reactiva(administradora, reportante):
    # Ley 1581: la supresión la decide el titular; el panel no puede deshacerla
    Usuario.objects.filter(pk=reportante.pk).update(is_active=False, suprimido_en=timezone.now())
    with pytest.raises(ValidationError, match="suprimida"):
        services.cambiar_estado_cuenta(actor=administradora, usuario_id=reportante.pk, activa=True)


def test_un_rol_invalido_se_rechaza(administradora, reportante):
    with pytest.raises(ValidationError):
        services.asignar_rol(actor=administradora, usuario_id=reportante.pk, rol="comercio")


def test_el_administrador_tambien_modera(administradora):
    assert es_moderador(administradora)
