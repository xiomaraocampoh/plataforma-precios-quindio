from django.db import models

from core.models import ModeloConMarcasDeTiempo


class Establecimiento(ModeloConMarcasDeTiempo):
    class Tipo(models.TextChoices):
        TIENDA_BARRIO = "tienda", "Tienda de barrio"
        MINIMERCADO = "minimercado", "Minimercado"
        SUPERMERCADO = "supermercado", "Supermercado"

    nombre = models.CharField(max_length=150)
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    direccion = models.CharField(max_length=200)
    barrio = models.CharField(max_length=100, blank=True)
    municipio = models.CharField(max_length=80, default="Armenia")
    latitud = models.DecimalField(max_digits=9, decimal_places=6)
    longitud = models.DecimalField(max_digits=9, decimal_places=6)
    activo = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["municipio", "barrio"])]

    def __str__(self) -> str:
        return f"{self.nombre} ({self.get_tipo_display()})"
