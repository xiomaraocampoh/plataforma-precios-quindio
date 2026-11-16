"""Casos de uso de cuentas (escritura)."""

import uuid

from django.contrib.auth.models import Group, Permission
from django.db import transaction
from django.utils import timezone

from .models import Usuario


def registrar_usuario(*, username: str, email: str, password: str) -> Usuario:
    """Crea un Reportante. Solo se invoca tras la autorización expresa de datos (Ley 1581)."""
    return Usuario.objects.create_user(
        username=username,
        email=email,
        password=password,
        rol=Usuario.Rol.REPORTANTE,
        acepto_tratamiento_datos=True,
        fecha_aceptacion_datos=timezone.now(),
    )


# Permisos del grupo «Moderadores» en /admin/ (RF-21, RF-22). Los que aún no existan se omiten.
PERMISOS_MODERACION = [
    "view_reporteprecio",
    "change_reporteprecio",
    "view_denuncia",
    "change_denuncia",
    "view_decisionmoderacion",
    "view_establecimiento",
    "change_establecimiento",
    "view_solicitudcatalogo",
    "change_solicitudcatalogo",
    "view_producto",
    "view_presentacion",
    "view_usuario",
    "change_usuario",
]
GRUPO_MODERADORES = "Moderadores"


def asegurar_grupo_moderadores() -> Group:
    grupo, _ = Group.objects.get_or_create(name=GRUPO_MODERADORES)
    grupo.permissions.set(Permission.objects.filter(codename__in=PERMISOS_MODERACION))
    return grupo


def asegurar_administrador(*, username: str, password: str) -> tuple[Usuario, bool]:
    """Superusuario de desarrollo. Si ya existe no se toca su contraseña."""
    existente = Usuario.objects.filter(username=username).first()
    if existente is not None:
        return existente, False
    return Usuario.objects.create_superuser(username=username, email="", password=password), True


def asegurar_moderador(*, username: str, password: str) -> tuple[Usuario, bool]:
    """Moderador con acceso a /admin/ (is_staff) y al grupo «Moderadores»."""
    usuario = Usuario.objects.filter(username=username).first()
    creado = usuario is None
    if creado:
        usuario = Usuario.objects.create_user(
            username=username,
            email="",
            password=password,
            rol=Usuario.Rol.MODERADOR,
            is_staff=True,
            acepto_tratamiento_datos=True,
            fecha_aceptacion_datos=timezone.now(),
        )
    usuario.groups.add(asegurar_grupo_moderadores())
    return usuario, creado


def actualizar_datos(*, usuario: Usuario, username: str, email: str) -> Usuario:
    """RF-03: el titular actualiza sus datos (Ley 1581, derecho de rectificación)."""
    usuario.username = username
    usuario.email = email
    usuario.save(update_fields=["username", "email"])
    return usuario


@transaction.atomic
def suprimir_cuenta(*, usuario: Usuario) -> Usuario:
    """RF-03: supresión de la cuenta (Ley 1581). Los aportes se conservan anonimizados.

    Los reportes, confirmaciones y denuncias siguen apuntando al mismo registro, pero este ya no
    contiene datos personales: alias aleatorio, sin correo ni nombre, sin contraseña utilizable e
    inactivo. Así la comparación no pierde precios y nadie puede volver a identificar al autor.
    """
    usuario.username = f"anonimo-{uuid.uuid4().hex[:12]}"
    usuario.email = ""
    usuario.first_name = ""
    usuario.last_name = ""
    usuario.is_active = False
    usuario.is_staff = False
    usuario.acepto_tratamiento_datos = False
    usuario.fecha_aceptacion_datos = None
    usuario.suprimido_en = timezone.now()
    usuario.set_unusable_password()
    usuario.save()
    usuario.groups.clear()
    return usuario


def suspender_cuenta(*, usuario_id: int) -> Usuario:
    """RF-22: no puede ingresar ni registrar; sus reportes quedan auditables."""
    usuario = Usuario.objects.get(pk=usuario_id)
    if usuario.is_staff or usuario.is_superuser:
        raise ValueError("No se puede suspender una cuenta de moderación o administración.")
    usuario.is_active = False
    usuario.save(update_fields=["is_active"])
    return usuario
