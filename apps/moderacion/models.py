from django.conf import settings
from django.db import models


class Denuncia(models.Model):
    """Reporte de información dudosa sobre un precio (EC-03)."""

    class Motivo(models.TextChoices):
        PRECIO_FALSO = "precio_falso", "Precio falso"
        PRODUCTO_EQUIVOCADO = "producto", "Producto o presentación equivocada"
        ESTABLECIMIENTO = "establecimiento", "Establecimiento equivocado"
        OTRO = "otro", "Otro"

    class Estado(models.TextChoices):
        ABIERTA = "abierta", "Abierta"
        ACEPTADA = "aceptada", "Aceptada"
        DESCARTADA = "descartada", "Descartada"

    reporte = models.ForeignKey(
        "precios.ReportePrecio", on_delete=models.CASCADE, related_name="denuncias"
    )
    denunciante = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="denuncias"
    )
    motivo = models.CharField(max_length=20, choices=Motivo.choices)
    detalle = models.TextField(blank=True)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.ABIERTA)
    creado_en = models.DateTimeField(auto_now_add=True)
    resuelto_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="denuncias_resueltas",
    )
    resuelto_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["reporte", "denunciante"], name="una_denuncia_por_usuario"
            ),
        ]

    def __str__(self) -> str:
        return f"Denuncia #{self.pk} ({self.estado})"
