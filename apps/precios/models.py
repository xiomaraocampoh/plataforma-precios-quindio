from django.conf import settings
from django.db import models

from .domain.vigencia import Fuente


class ReportePrecio(models.Model):
    """Precio observado. El autor es dato personal: nunca se expone en público (M-15)."""

    class Estado(models.TextChoices):
        PUBLICADO = "publicado", "Publicado"
        EN_REVISION = "en_revision", "En revisión"
        RECHAZADO = "rechazado", "Rechazado"

    presentacion = models.ForeignKey(
        "catalogo.Presentacion", on_delete=models.PROTECT, related_name="reportes"
    )
    establecimiento = models.ForeignKey(
        "establecimientos.Establecimiento", on_delete=models.PROTECT, related_name="reportes"
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reportes"
    )
    fuente = models.CharField(
        max_length=12, choices=[(f.value, f.value) for f in Fuente], default=Fuente.REPORTANTE.value
    )
    precio = models.DecimalField(max_digits=12, decimal_places=2)
    fecha_observacion = models.DateTimeField()
    creado_en = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PUBLICADO)
    # Idempotencia para registros hechos sin señal y sincronizados después (M-22)
    id_cliente = models.UUIDField(null=True, blank=True, unique=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(precio__gt=0), name="precio_positivo"),
        ]
        indexes = [
            models.Index(
                fields=["presentacion", "establecimiento", "-fecha_observacion"],
                name="idx_reporte_ultimo",
            ),
            models.Index(fields=["estado", "-fecha_observacion"], name="idx_reporte_estado"),
        ]

    def __str__(self) -> str:
        return f"{self.presentacion} @ {self.establecimiento}: {self.precio}"
