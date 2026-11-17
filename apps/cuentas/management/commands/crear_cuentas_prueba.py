"""Crea o actualiza las cuentas de prueba de cada rol.

Uso: CUENTAS_PRUEBA_PASSWORD=... python manage.py crear_cuentas_prueba

La contraseña sale SOLO de la variable de entorno. Sin ella el comando se detiene: no genera ni
imprime contraseñas. Documentación: docs/nucleo/cuentas-de-prueba.md
"""

import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.cuentas import services
from apps.cuentas.domain.cuentas_prueba import (
    VARIABLE_CONTRASENA,
    ContrasenaDePruebaAusenteError,
    exigir_contrasena_de_prueba,
)


class Command(BaseCommand):
    help = "Crea o actualiza las cuentas de prueba (una por rol) con CUENTAS_PRUEBA_PASSWORD."

    def handle(self, *args, **opciones):
        try:
            contrasena = exigir_contrasena_de_prueba(os.environ.get(VARIABLE_CONTRASENA))
        except ContrasenaDePruebaAusenteError as exc:
            raise CommandError(str(exc)) from exc
        try:
            cuentas = services.cuentas_prueba.asegurar_cuentas_prueba(contrasena=contrasena)
        except ValidationError as exc:  # el mensaje del validador nunca incluye la contraseña
            raise CommandError(
                f"La contraseña de {VARIABLE_CONTRASENA} no cumple las reglas: "
                + " ".join(exc.messages)
            ) from exc
        self._tabla(cuentas)
        self.stdout.write(f"Contraseña tomada de {VARIABLE_CONTRASENA} (no se muestra).")
        if getattr(settings, "PERMITIR_PRUEBA_SIN_2FA", False) and settings.DEBUG:
            self.stdout.write(
                self.style.WARNING("PERMITIR_PRUEBA_SIN_2FA activo: estas cuentas omiten el 2FA.")
            )

    def _tabla(self, cuentas) -> None:
        ancho_u = max(len(c.usuario) for c, _ in cuentas)
        ancho_r = max(len(c.rol) for c, _ in cuentas)
        self.stdout.write(f"{'Usuario':<{ancho_u}}  {'Rol':<{ancho_r}}  Estado  Qué puede probar")
        for cuenta, creada in cuentas:
            estado = "creada" if creada else "actual."
            self.stdout.write(
                f"{cuenta.usuario:<{ancho_u}}  {cuenta.rol:<{ancho_r}}  {estado:<7} "
                f"{cuenta.puede_probar}"
            )
        self.stdout.write(self.style.SUCCESS(f"Listo: {len(cuentas)} cuentas de prueba."))
