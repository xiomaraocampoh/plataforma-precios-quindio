from django.db import models

from core.models import ModeloConMarcasDeTiempo

from .domain.normalizacion import Unidad


class Categoria(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    perecedera = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.nombre


class Producto(ModeloConMarcasDeTiempo):
    """Producto genérico (p. ej. 'Arroz blanco'). Sus presentaciones se comparan por unidad."""

    nombre = models.CharField(max_length=150)
    marca = models.CharField(max_length=80, blank=True)
    nombre_normalizado = models.CharField(max_length=200, db_index=True)  # D-05 duplicados
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="productos")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["nombre_normalizado", "marca"], name="producto_unico_por_marca"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.nombre} {self.marca}".strip()


class Presentacion(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="presentaciones")
    cantidad = models.DecimalField(max_digits=10, decimal_places=3)
    unidad = models.CharField(max_length=4, choices=[(u.value, u.value) for u in Unidad])
    codigo_barras = models.CharField(max_length=14, blank=True, db_index=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(cantidad__gt=0), name="cantidad_positiva"),
            models.UniqueConstraint(
                fields=["producto", "cantidad", "unidad"], name="presentacion_unica"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.producto} {self.cantidad.normalize()} {self.unidad}"
