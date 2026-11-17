"""Cuentas de prueba por rol (crear_cuentas_prueba). Capa de aplicación.

Crea o actualiza las cuentas de `domain.cuentas_prueba.CUENTAS_PRUEBA`: correo ya verificado,
consentimiento de datos aceptado (Ley 1581), grupo del rol y la marca `es_cuenta_prueba`, que es lo
único que les permite omitir el 2FA en local (PERMITIR_PRUEBA_SIN_2FA + DEBUG). No envía correos.

La escritura es la MISMA que hace la migración `cuentas.0006_semilla_cuentas_prueba`
(`apps/cuentas/semilla.py`, ADR-0023); aquí se añade la validación de la contraseña.
"""

from django.apps import apps as registro
from django.contrib.auth.password_validation import validate_password
from django.db import transaction

from .. import semilla
from ..domain.cuentas_prueba import CUENTAS_PRUEBA, CuentaPrueba
from ..models import Usuario


@transaction.atomic
def asegurar_cuentas_prueba(*, contrasena: str | None) -> list[tuple[CuentaPrueba, bool]]:
    """Devuelve (cuenta, creada) por cada cuenta de prueba.

    Con `contrasena` se fija en todas (se valida con AUTH_PASSWORD_VALIDATORS antes de escribir
    nada). Sin ella (cargar_datos_prueba solo necesita autores) las nuevas quedan sin contraseña
    utilizable y las existentes conservan la suya.
    """
    if contrasena:
        for cuenta in CUENTAS_PRUEBA:  # con cada cuenta: el validador compara con usuario y correo
            validate_password(contrasena, Usuario(username=cuenta.usuario, email=cuenta.correo))
    return semilla.sembrar(registro, contrasena=contrasena, fijar_en_existentes=True)


def usuarios_de_prueba() -> dict[str, Usuario]:
    """Las cuentas de prueba existentes, por nombre de usuario."""
    return semilla.autores(registro)
