from django.db import models


class PrecioReferencia(models.Model):
    """RF-07: precio mayorista de referencia (SIPSA, DANE). Se muestra aparte del ranking."""

    class Fuente(models.TextChoices):
        SIPSA = "sipsa", "SIPSA (DANE)"

    producto = models.ForeignKey(
        "catalogo.Producto", on_delete=models.PROTECT, related_name="referencias"
    )
    mercado = models.CharField(max_length=120)
    precio_por_kg = models.DecimalField(max_digits=12, decimal_places=2)
    fecha = models.DateField()
    fuente = models.CharField(max_length=10, choices=Fuente.choices, default=Fuente.SIPSA)
    importado_en = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(precio_por_kg__gt=0), name="referencia_precio_positivo"
            ),
            models.UniqueConstraint(
                fields=["producto", "mercado", "fecha", "fuente"], name="referencia_unica"
            ),
        ]
        indexes = [models.Index(fields=["producto", "-fecha"], name="idx_referencia_producto")]

    def __str__(self) -> str:
        return f"{self.producto} · {self.mercado} · {self.precio_por_kg}/kg ({self.fecha})"
