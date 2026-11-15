"""Casos de uso de cuentas (escritura)."""

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
