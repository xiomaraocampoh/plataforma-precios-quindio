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


class DecisionModeracion(models.Model):
    """RF-21, RF-22: cada decisión de moderación guarda quién la tomó y cuándo (M-14)."""

    class Accion(models.TextChoices):
        APROBAR_REPORTE = "aprobar_reporte", "Aprobar reporte"
        RECHAZAR_REPORTE = "rechazar_reporte", "Rechazar reporte"
        ACEPTAR_DENUNCIA = "aceptar_denuncia", "Aceptar denuncia"
        DESCARTAR_DENUNCIA = "descartar_denuncia", "Descartar denuncia"
        APROBAR_SOLICITUD = "aprobar_solicitud", "Aprobar solicitud de catálogo"
        RECHAZAR_SOLICITUD = "rechazar_solicitud", "Rechazar solicitud de catálogo"
        APROBAR_ESTABLECIMIENTO = "aprobar_establecimiento", "Aprobar establecimiento"
        RECHAZAR_ESTABLECIMIENTO = "rechazar_establecimiento", "Rechazar establecimiento"
        SUSPENDER_CUENTA = "suspender_cuenta", "Suspender cuenta"

    moderador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="decisiones_moderacion"
    )
    accion = models.CharField(max_length=30, choices=Accion.choices)
    objeto_tipo = models.CharField(max_length=20)
    objeto_id = models.PositiveIntegerField()
    motivo = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["objeto_tipo", "objeto_id"], name="idx_decision_objeto"),
            models.Index(fields=["-creado_en"], name="idx_decision_fecha"),
        ]

    def __str__(self) -> str:
        return f"{self.get_accion_display()} #{self.objeto_id} por {self.moderador}"
