"""Siembra de los grupos de rol y las cuentas de prueba (ADR-0023).

La usan la migración `0006_semilla_cuentas_prueba` y el servicio de `crear_cuentas_prueba`.
Recibe el registro de modelos (`apps`). Los modelos históricos no tienen `set_password`: la clave
se fija con `make_password`, que también produce la contraseña inutilizable cuando no hay clave.

La contraseña llega como argumento (sale de CUENTAS_PRUEBA_PASSWORD) y nunca se imprime.
El correo sale de `domain.cuentas_prueba.correo_de_prueba` con CUENTAS_PRUEBA_CORREO_BASE (ajuste);
si la base no es válida, CorreoBaseInvalidoError detiene la siembra antes de escribir.
"""

from django.conf import settings
from django.contrib.auth.hashers import is_password_usable, make_password
from django.db import transaction
from django.db.models import ProtectedError, Q
from django.utils import timezone

from .domain.cuentas_prueba import CUENTAS_PRUEBA, CuentaPrueba, correos_de_prueba
from .domain.roles import GRUPOS, PERMISOS, grupo_de


def _permisos(permiso_modelo, nombres):
    filtro = Q(pk__in=[])
    for nombre in nombres:
        app, codigo = nombre.split(".", 1)
        filtro |= Q(content_type__app_label=app, codename=codigo)
    return permiso_modelo.objects.filter(filtro)


def asegurar_grupos(apps) -> dict[str, object]:
    """Los grupos de rol por nombre. Si falta alguno se crea con sus permisos; los que ya
    existen no se tocan (un administrador pudo ajustarlos)."""
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    grupos = {}
    for rol, nombre in GRUPOS.items():
        grupo, creado = Group.objects.get_or_create(name=nombre)
        if creado:
            grupo.permissions.set(_permisos(Permission, PERMISOS[rol]))
        grupos[nombre] = grupo
    return grupos


def correos() -> dict[str, str]:
    """El correo de cada cuenta de prueba según CUENTAS_PRUEBA_CORREO_BASE, por usuario."""
    return correos_de_prueba(getattr(settings, "CUENTAS_PRUEBA_CORREO_BASE", ""))


def _aplicar(usuario, cuenta: CuentaPrueba, correo: str, ahora) -> None:
    usuario.rol = cuenta.rol
    usuario.email = correo
    usuario.email_verificado_en = usuario.email_verificado_en or ahora
    usuario.acepto_tratamiento_datos = True
    usuario.fecha_aceptacion_datos = usuario.fecha_aceptacion_datos or ahora
    usuario.is_staff = cuenta.staff
    usuario.is_superuser = cuenta.superusuario
    usuario.is_active = cuenta.activa
    usuario.es_cuenta_prueba = True


def _sincronizar_grupo(usuario, grupos: dict) -> None:
    """Solo en el grupo de su rol; los grupos que no son de rol se conservan."""
    objetivo = grupos.get(grupo_de(usuario.rol) or "")
    sobrantes = [g for g in grupos.values() if g is not objetivo]
    usuario.groups.remove(*sobrantes)
    if objetivo is not None:
        usuario.groups.add(objetivo)


def _tiene_clave_utilizable(usuario) -> bool:
    return bool(usuario.password) and is_password_usable(usuario.password)


def sembrar(
    apps, *, contrasena: str | None, fijar_en_existentes: bool
) -> list[tuple[CuentaPrueba, bool]]:
    """Crea o actualiza las cuentas de prueba; devuelve (cuenta, creada).

    - Con `contrasena`: la fijan las cuentas nuevas, las que no tenían una utilizable y, si
      `fijar_en_existentes`, todas (así cambia la clave `crear_cuentas_prueba`).
    - Sin `contrasena`: las nuevas quedan con contraseña inutilizable; las demás conservan la suya.
    La validación de la contraseña (AUTH_PASSWORD_VALIDATORS) la hace quien llama.
    """
    Usuario = apps.get_model("cuentas", "Usuario")
    por_usuario = correos()  # primero: una base inválida no deja nada a medias
    grupos = asegurar_grupos(apps)
    ahora = timezone.now()
    resultado = []
    for cuenta in CUENTAS_PRUEBA:
        usuario = Usuario.objects.filter(username=cuenta.usuario).first()
        creada = usuario is None
        if creada:
            usuario = Usuario(username=cuenta.usuario)
        _aplicar(usuario, cuenta, por_usuario[cuenta.usuario], ahora)
        if contrasena and (fijar_en_existentes or not _tiene_clave_utilizable(usuario)):
            usuario.password = make_password(contrasena)
        elif not _tiene_clave_utilizable(usuario):
            usuario.password = make_password(None)  # inutilizable: «!» + texto aleatorio
        usuario.save()
        _sincronizar_grupo(usuario, grupos)
        resultado.append((cuenta, creada))
    return resultado


def actualizar_correos(apps) -> list[tuple[CuentaPrueba, str]]:
    """Solo el correo de las cuentas de prueba que ya existen (`es_cuenta_prueba=True`); no crea
    cuentas ni toca contraseña, rol, grupo o estado. Devuelve (cuenta, correo) de las actualizadas.
    """
    Usuario = apps.get_model("cuentas", "Usuario")
    por_usuario = correos()
    actualizadas = []
    for cuenta in CUENTAS_PRUEBA:
        correo = por_usuario[cuenta.usuario]
        filtro = Usuario.objects.filter(username=cuenta.usuario, es_cuenta_prueba=True)
        if filtro.update(email=correo):
            actualizadas.append((cuenta, correo))
    return actualizadas


def autores(apps) -> dict:
    """Las cuentas de prueba existentes, por nombre de usuario."""
    Usuario = apps.get_model("cuentas", "Usuario")
    nombres = [c.usuario for c in CUENTAS_PRUEBA]
    return {u.username: u for u in Usuario.objects.filter(username__in=nombres)}


def revertir(apps) -> int:
    """Borra las cuentas de prueba que no tienen aportes reales (PROTECT). Los grupos se quedan:
    los creó `administracion.0002` y quitarlos dejaría a otros usuarios sin permisos."""
    Usuario = apps.get_model("cuentas", "Usuario")
    nombres = [c.usuario for c in CUENTAS_PRUEBA]
    borradas = 0
    for usuario in Usuario.objects.filter(username__in=nombres, es_cuenta_prueba=True):
        try:
            with transaction.atomic():
                usuario.delete()
        except ProtectedError:
            continue
        borradas += 1
    return borradas
