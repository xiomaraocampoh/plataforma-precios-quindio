from django.conf import settings
from django.db import models

from core.models import ModeloConMarcasDeTiempo

from .domain.normalizacion import Unidad, formatear_cantidad


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
        return f"{self.producto} {formatear_cantidad(self.cantidad)} {self.unidad}"


class SolicitudCatalogo(models.Model):
    """RF-06: alta de un producto o presentación pedida por un reportante (pasa por moderación)."""

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        APROBADA = "aprobada", "Aprobada"
        RECHAZADA = "rechazada", "Rechazada"

    nombre = models.CharField(max_length=150)
    marca = models.CharField(max_length=80, blank=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="solicitudes")
    cantidad = models.DecimalField(max_digits=10, decimal_places=3)
    unidad = models.CharField(max_length=4, choices=[(u.value, u.value) for u in Unidad])
    codigo_barras = models.CharField(max_length=14, blank=True)
    detalle = models.TextField(blank=True)
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="solicitudes_catalogo"
    )
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    creado_en = models.DateTimeField(auto_now_add=True)
    resuelto_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="solicitudes_resueltas",
    )
    resuelto_en = models.DateTimeField(null=True, blank=True)
    presentacion_creada = models.ForeignKey(
        Presentacion, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad__gt=0), name="solicitud_cantidad_positiva"
            ),
        ]
        indexes = [models.Index(fields=["estado", "creado_en"], name="idx_solicitud_estado")]

    def __str__(self) -> str:
        texto = f"{self.nombre} {self.marca}".strip()
        return f"{texto} {formatear_cantidad(self.cantidad)} {self.unidad} ({self.estado})"
