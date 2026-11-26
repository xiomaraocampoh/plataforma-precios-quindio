from django.conf import settings
from django.db import models

from core.models import ModeloConMarcasDeTiempo


class Establecimiento(ModeloConMarcasDeTiempo):
    class Tipo(models.TextChoices):
        TIENDA_BARRIO = "tienda", "Tienda de barrio"
        MINIMERCADO = "minimercado", "Minimercado"
        SUPERMERCADO = "supermercado", "Supermercado"
        DISCOUNT = "discount", "Tienda de descuento"
        PLAZA = "plaza", "Plaza de mercado"

    class Estado(models.TextChoices):
        APROBADO = "aprobado", "Aprobado"
        PENDIENTE = "pendiente", "Pendiente de moderación"
        RECHAZADO = "rechazado", "Rechazado"

    nombre = models.CharField(max_length=150)
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    direccion = models.CharField(max_length=200)
    barrio = models.CharField(max_length=100, blank=True)
    municipio = models.CharField(max_length=80, default="Armenia")
    # RF-09: opcionales para las sugerencias (quien sugiere rara vez conoce las coordenadas)
    latitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    activo = models.BooleanField(default=True)
    # RF-10: un establecimiento sugerido queda pendiente e inactivo hasta que se aprueba
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.APROBADO)
    sugerido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="establecimientos_sugeridos",
    )
    revisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="establecimientos_revisados",
    )
    revisado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["municipio", "barrio"]),
            models.Index(fields=["estado", "creado_en"], name="idx_establecimiento_estado"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(estado="pendiente") | models.Q(activo=False),
                name="establecimiento_pendiente_inactivo",
            ),
            models.CheckConstraint(
                condition=models.Q(latitud__isnull=True, longitud__isnull=True)
                | models.Q(
                    latitud__gte=-90, latitud__lte=90, longitud__gte=-180, longitud__lte=180
                ),
                name="establecimiento_coordenadas_validas",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.nombre} ({self.get_tipo_display()})"
