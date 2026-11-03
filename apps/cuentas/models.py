from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """Usuario personalizado desde el día 1 (cambiarlo después exige migraciones costosas)."""

    class Rol(models.TextChoices):
        REPORTANTE = "reportante", "Reportante"
        COMERCIO = "comercio", "Comercio"
        MODERADOR = "moderador", "Moderador"

    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.REPORTANTE)
    # Ley 1581 de 2012: autorización expresa del titular
    acepto_tratamiento_datos = models.BooleanField(default=False)
    fecha_aceptacion_datos = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return self.username
