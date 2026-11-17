"""Aviso al arrancar (runserver, migrate, check) si las cuentas de prueba omiten el 2FA."""

from django.conf import settings
from django.core.checks import Tags, Warning, register


@register(Tags.security)
def aviso_prueba_sin_2fa(app_configs=None, **kwargs):
    if not getattr(settings, "PERMITIR_PRUEBA_SIN_2FA", False):
        return []
    if settings.DEBUG:
        return [
            Warning(
                "PERMITIR_PRUEBA_SIN_2FA está activo: las cuentas de prueba entran sin "
                "verificación en dos pasos. Solo para desarrollo local.",
                hint="Quítelo del .env cuando termine. En producción siempre es False.",
                id="cuentas.W001",
            )
        ]
    return [
        Warning(
            "PERMITIR_PRUEBA_SIN_2FA está activo pero DEBUG=False: se ignora y todas las "
            "cuentas siguen pidiendo el segundo paso.",
            id="cuentas.W002",
        )
    ]
