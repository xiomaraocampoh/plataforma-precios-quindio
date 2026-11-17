"""Cuentas de prueba por rol (crear_cuentas_prueba). Capa de aplicación.

Crea o actualiza las cuentas de `domain.cuentas_prueba.CUENTAS_PRUEBA`: correo ya verificado,
consentimiento de datos aceptado (Ley 1581), grupo del rol y la marca `es_cuenta_prueba`, que es lo
único que les permite omitir el 2FA en local (PERMITIR_PRUEBA_SIN_2FA + DEBUG). No envía correos.
"""

from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils import timezone

from ..domain.cuentas_prueba import CUENTAS_PRUEBA, CuentaPrueba
from ..models import Usuario
from .basicos import sincronizar_grupo_de_rol


def _aplicar(usuario: Usuario, cuenta: CuentaPrueba, ahora) -> None:
    usuario.rol = cuenta.rol
    usuario.email = cuenta.correo
    usuario.email_verificado_en = usuario.email_verificado_en or ahora
    usuario.acepto_tratamiento_datos = True
    usuario.fecha_aceptacion_datos = usuario.fecha_aceptacion_datos or ahora
    usuario.is_staff = cuenta.staff
    usuario.is_superuser = cuenta.superusuario
    usuario.is_active = cuenta.activa
    usuario.es_cuenta_prueba = True


@transaction.atomic
def asegurar_cuentas_prueba(*, contrasena: str | None) -> list[tuple[CuentaPrueba, bool]]:
    """Devuelve (cuenta, creada) por cada cuenta de prueba.

    Con `contrasena` se fija en todas (se valida con AUTH_PASSWORD_VALIDATORS). Sin ella
    (cargar_datos_prueba solo necesita autores) las nuevas quedan sin contraseña utilizable y las
    existentes conservan la suya.
    """
    ahora = timezone.now()
    resultado = []
    for cuenta in CUENTAS_PRUEBA:
        usuario = Usuario.objects.filter(username=cuenta.usuario).first()
        creada = usuario is None
        if creada:
            usuario = Usuario(username=cuenta.usuario)
        _aplicar(usuario, cuenta, ahora)
        if contrasena:
            validate_password(contrasena, usuario)
            usuario.set_password(contrasena)
        elif creada:
            usuario.set_unusable_password()
        usuario.save()
        sincronizar_grupo_de_rol(usuario)
        resultado.append((cuenta, creada))
    return resultado


def usuarios_de_prueba() -> dict[str, Usuario]:
    """Las cuentas de prueba existentes, por nombre de usuario."""
    nombres = [c.usuario for c in CUENTAS_PRUEBA]
    return {u.username: u for u in Usuario.objects.filter(username__in=nombres)}
