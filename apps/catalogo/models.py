from django.conf import settings
from django.db import models
from django.db.models.functions import Length
from django.db.models.lookups import Exact

from core.models import ModeloConMarcasDeTiempo

from .domain.duplicados import normalizar_nombre
from .domain.grupos import GRUPOS
from .domain.normalizacion import Unidad, formatear_cantidad


class Marca(models.Model):
    """Marca del producto. Única por nombre normalizado: «Águila Roja» = «aguila roja»."""

    nombre = models.CharField(max_length=80)
    nombre_normalizado = models.CharField(max_length=80, unique=True)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self) -> str:
        return self.nombre

    def save(self, *args, **kwargs):
        self.nombre = " ".join(self.nombre.split())
        self.nombre_normalizado = normalizar_nombre(self.nombre)
        super().save(*args, **kwargs)


class Categoria(models.Model):
    class Grupo(models.TextChoices):
        """Departamento amplio (como en un supermercado); mismos valores que domain/grupos.py."""

        MERCADO = "mercado", "Mercado"
        FRUTAS_VERDURAS = "frutas_verduras", "Frutas y verduras"
        CARNES_PESCADO = "carnes_pescado", "Carnes y pescado"
        LACTEOS_HUEVOS = "lacteos_huevos", "Lácteos y huevos"
        BEBIDAS = "bebidas", "Bebidas"
        ASEO_HOGAR = "aseo_hogar", "Aseo del hogar"
        SALUD_BELLEZA = "salud_belleza", "Salud y belleza"
        OTROS = "otros", "Otros"

    nombre = models.CharField(max_length=80, unique=True)
    grupo = models.CharField(max_length=20, choices=Grupo.choices, default=Grupo.OTROS)
    perecedera = models.BooleanField(default=False)
    activa = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(grupo__in=[g.valor for g in GRUPOS]),
                name="categoria_grupo_valido",
            )
        ]

    def __str__(self) -> str:
        return self.nombre


class Producto(ModeloConMarcasDeTiempo):
    """Producto genérico (p. ej. 'Arroz blanco'). Sus presentaciones se comparan por unidad."""

    nombre = models.CharField(max_length=150)
    marca = models.ForeignKey(
        Marca, on_delete=models.PROTECT, null=True, blank=True, related_name="productos"
    )
    nombre_normalizado = models.CharField(max_length=200, db_index=True)  # D-05 duplicados
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="productos")
    descripcion = models.CharField(max_length=500, blank=True, default="")
    activo = models.BooleanField(default=True)

    class Meta:
        constraints = [
            # Con NULL la unicidad no se cumpliría: un índice parcial para cada caso
            models.UniqueConstraint(
                fields=["nombre_normalizado", "marca"],
                condition=models.Q(marca__isnull=False),
                name="producto_unico_por_marca",
            ),
            models.UniqueConstraint(
                fields=["nombre_normalizado"],
                condition=models.Q(marca__isnull=True),
                name="producto_unico_sin_marca",
            ),
        ]

    def __str__(self) -> str:
        # Las consultas que listan productos hacen select_related("marca") (sin N+1)
        return f"{self.nombre} {self.marca or ''}".strip()

    @property
    def foto_version(self) -> str:
        """Versión de la foto (vacía = sin foto). Sirve para versionar la URL y la caché.

        Lee la relación `foto`: los listados usan `selectors.con_fotos(...)` (join sin los bytes)
        para no hacer una consulta por producto.
        """
        try:
            return self.foto.version
        except FotoProducto.DoesNotExist:
            return ""

    def save(self, *args, **kwargs):
        self.nombre_normalizado = normalizar_nombre(self.nombre)  # D-05: siempre la misma regla
        super().save(*args, **kwargs)


class Presentacion(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="presentaciones")
    cantidad = models.DecimalField(max_digits=10, decimal_places=3)
    unidad = models.CharField(max_length=4, choices=[(u.value, u.value) for u in Unidad])
    codigo_barras = models.CharField(max_length=14, blank=True, db_index=True)
    activa = models.BooleanField(default=True)

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


class FotoProducto(models.Model):
    """Miniatura WebP cuadrada de un producto (ADR-0024). Una por producto.

    La imagen guardada la genera el servidor (`catalogo/imagenes.py`); nunca es el archivo subido.
    Composición real: si el producto se borra, su foto también (on_delete=CASCADE).
    """

    producto = models.OneToOneField(Producto, on_delete=models.CASCADE, related_name="foto")
    contenido = models.BinaryField()
    tipo_contenido = models.CharField(max_length=30, default="image/webp")
    # Huella corta del contenido: la misma foto da la misma URL y una distinta la cambia
    version = models.CharField(max_length=12)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(Exact(Length("version"), 12)), name="foto_version_de_12"
            ),
        ]

    def __str__(self) -> str:
        return f"Foto de {self.producto}"
