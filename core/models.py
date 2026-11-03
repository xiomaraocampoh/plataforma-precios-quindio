from django.db import models


class ModeloConMarcasDeTiempo(models.Model):
    """Base abstracta: trazabilidad mínima de creación/modificación (M-14)."""

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
