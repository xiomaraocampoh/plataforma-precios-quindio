"""Casos de uso de cuentas (escritura)."""

import uuid

from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from ..domain.roles import (
    GRUPOS,
    PERMISOS,
    CambioDeCuentaNoPermitidoError,
    Rol,
    grupo_de,
    validar_cambio_de_cuenta,
)
from ..models import CodigoRespaldo, DispositivoConocido, SegundoFactor, Usuario
from . import correo


def registrar_usuario(*, username: str, email: str, password: str) -> Usuario:
    """Crea un Reportante. Solo se invoca tras la autorización expresa de datos (Ley 1581).
    Si dio un correo, recibe el enlace para confirmarlo (RF-24)."""
    usuario = Usuario.objects.create_user(
        username=username,
        email=email,
        password=password,
        rol=Usuario.Rol.REPORTANTE,
        acepto_tratamiento_datos=True,
        fecha_aceptacion_datos=timezone.now(),
    )
    correo.enviar_verificacion(usuario)
    return usuario


def permisos_por_nombre(nombres) -> list[Permission]:
    """Permission a partir de "app_label.codename" (como en user.has_perm)."""
    filtro = Q(pk__in=[])
    for nombre in nombres:
        app, codigo = nombre.split(".", 1)
        filtro |= Q(content_type__app_label=app, codename=codigo)
    return list(Permission.objects.filter(filtro))


def asegurar_grupo(rol: str) -> Group | None:
    """Grupo del rol con sus permisos (lo crea la migración; aquí se recrea si falta)."""
    nombre = grupo_de(rol)
    if nombre is None:
        return None
    grupo, creado = Group.objects.get_or_create(name=nombre)
    if creado:
        grupo.permissions.set(permisos_por_nombre(PERMISOS[Rol(rol)]))
    return grupo


def sincronizar_grupo_de_rol(usuario: Usuario) -> None:
    """El usuario queda solo en el grupo de su rol; los grupos que no son de rol se conservan."""
    objetivo = asegurar_grupo(usuario.rol)
    sobrantes = usuario.groups.filter(name__in=GRUPOS.values())
    if objetivo is not None:
        sobrantes = sobrantes.exclude(pk=objetivo.pk)
        usuario.groups.add(objetivo)
    usuario.groups.remove(*sobrantes)


def _validar_actor(actor, usuario: Usuario) -> None:
    try:
        validar_cambio_de_cuenta(
            actor_id=actor.pk,
            objetivo_id=usuario.pk,
            actor_es_superusuario=actor.is_superuser,
            objetivo_es_superusuario=usuario.is_superuser,
        )
    except CambioDeCuentaNoPermitidoError as exc:
        raise ValidationError(str(exc)) from exc


@transaction.atomic
def asignar_rol(*, actor, usuario_id: int, rol: str) -> Usuario:
    """Un administrador asigna uno de los roles con grupo (no el suyo propio)."""
    if grupo_de(rol) is None:
        raise ValidationError("Elige un rol válido.")
    usuario = Usuario.objects.select_for_update().get(pk=usuario_id)
    _validar_actor(actor, usuario)
    usuario.rol = rol
    usuario.save(update_fields=["rol"])  # la señal sincroniza el grupo
    return usuario


@transaction.atomic
def cambiar_estado_cuenta(*, actor, usuario_id: int, activa: bool) -> Usuario:
    """Activa o suspende una cuenta desde el panel (nunca la propia)."""
    usuario = Usuario.objects.select_for_update().get(pk=usuario_id)
    _validar_actor(actor, usuario)
    if activa and usuario.suprimido_en is not None:
        raise ValidationError(
            "La cuenta fue suprimida por su titular (Ley 1581 de 2012); no se puede reactivar."
        )
    estaba_activa = usuario.is_active
    usuario.is_active = activa
    usuario.save(update_fields=["is_active"])
    if estaba_activa and not activa:
        correo.notificar_suspension(usuario)
    return usuario


def asegurar_administrador(*, username: str, password: str) -> tuple[Usuario, bool]:
    """Superusuario de desarrollo. Si ya existe no se toca su contraseña."""
    existente = Usuario.objects.filter(username=username).first()
    if existente is not None:
        return existente, False
    return Usuario.objects.create_superuser(username=username, email="", password=password), True


def asegurar_moderador(*, username: str, password: str) -> tuple[Usuario, bool]:
    """Moderador con acceso a /admin/ (is_staff) y al grupo «Moderador»."""
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
    sincronizar_grupo_de_rol(usuario)
    return usuario, creado


def actualizar_datos(*, usuario: Usuario, username: str, email: str) -> Usuario:
    """RF-03: el titular actualiza sus datos (Ley 1581, derecho de rectificación)."""
    cambio_correo = usuario.email.lower() != (email or "").lower()
    usuario.username = username
    usuario.email = email
    campos = ["username", "email"]
    if cambio_correo:  # un correo nuevo se vuelve a confirmar (RF-24)
        usuario.email_verificado_en = None
        campos.append("email_verificado_en")
    usuario.save(update_fields=campos)
    if cambio_correo:
        correo.enviar_verificacion(usuario)
    return usuario


@transaction.atomic
def suprimir_cuenta(*, usuario: Usuario) -> Usuario:
    """RF-03: supresión de la cuenta (Ley 1581). Los aportes se conservan anonimizados.

    Los reportes, confirmaciones y denuncias siguen apuntando al mismo registro, pero este ya no
    contiene datos personales: alias aleatorio, sin correo ni nombre, sin contraseña utilizable e
    inactivo. Así la comparación no pierde precios y nadie puede volver a identificar al autor.
    """
    correo.notificar_supresion(usuario)  # antes de borrar el correo; la cola lo redacta al enviar
    usuario.username = f"anonimo-{uuid.uuid4().hex[:12]}"
    usuario.email = ""
    usuario.email_verificado_en = None
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
    SegundoFactor.objects.filter(usuario=usuario).delete()
    CodigoRespaldo.objects.filter(usuario=usuario).delete()
    DispositivoConocido.objects.filter(usuario=usuario).delete()
    return usuario


def suspender_cuenta(*, usuario_id: int) -> Usuario:
    """RF-22: no puede ingresar ni registrar; sus reportes quedan auditables."""
    usuario = Usuario.objects.get(pk=usuario_id)
    if usuario.is_staff or usuario.is_superuser:
        raise ValueError("No se puede suspender una cuenta de moderación o administración.")
    usuario.is_active = False
    usuario.save(update_fields=["is_active"])
    correo.notificar_suspension(usuario)
    return usuario
