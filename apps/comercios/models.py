"""Persistencia del módulo comercial (Corte III). Solo tablas nuevas: el núcleo no cambia (EC-05).

Datos personales (Ley 1581): el usuario dueño del perfil, el teléfono y los documentos de
verificación (ADR-0034) NUNCA salen en una respuesta pública. La comparación solo recibe precios y
promociones por establecimiento, a través del puerto del ADR-012.
"""

from django.conf import settings
from django.db import models
from django.db.models import Q

from .domain.documentos import MAX_BYTES_DOCUMENTO
from .domain.promociones import MotivoPromocion, TipoPromocion


class PerfilComercio(models.Model):
    """RF-C01: perfil voluntario vinculado a un establecimiento del directorio.

    RF-C02 / ADR-015: queda pendiente hasta que un moderador lo verifica. La verificación vive aquí
    (`verificado_por`, `verificado_en`) y no en `moderacion`, para no migrar tablas del núcleo.
    """

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente de verificación"
        VERIFICADO = "verificado", "Verificado"
        RECHAZADO = "rechazado", "No verificado"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="perfiles_comercio"
    )
    establecimiento = models.ForeignKey(
        "establecimientos.Establecimiento",
        on_delete=models.PROTECT,
        related_name="perfiles_comercio",
    )
    nombre_contacto = models.CharField(max_length=120)
    telefono = models.CharField(max_length=20, blank=True)
    # ADR-0034: la evidencia son dos PDF (DocumentoComercio). Este texto ya no se pide; la semilla
    # lo usa como marcador de los perfiles de prueba (ADR-0023).
    evidencia = models.CharField(max_length=300, blank=True)
    codigo_verificacion = models.CharField(max_length=12)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    verificado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="comercios_verificados",
    )
    verificado_en = models.DateTimeField(null=True, blank=True)
    motivo_decision = models.CharField(max_length=300, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "perfil de comercio"
        verbose_name_plural = "perfiles de comercio"
        constraints = [
            # Un perfil activo (pendiente o verificado) por establecimiento y por usuario
            models.UniqueConstraint(
                fields=["establecimiento"],
                condition=~Q(estado="rechazado"),
                name="un_perfil_activo_por_establecimiento",
            ),
            models.UniqueConstraint(
                fields=["usuario"],
                condition=~Q(estado="rechazado"),
                name="un_perfil_activo_por_usuario",
            ),
            # Una decisión siempre tiene quién y cuándo (M-14)
            models.CheckConstraint(
                condition=Q(estado="pendiente")
                | Q(verificado_por__isnull=False, verificado_en__isnull=False),
                name="perfil_decidido_con_moderador_y_fecha",
            ),
        ]
        indexes = [models.Index(fields=["estado", "creado_en"], name="idx_perfil_estado")]

    def __str__(self) -> str:
        return f"{self.establecimiento} ({self.get_estado_display()})"

    @property
    def verificado(self) -> bool:
        return self.estado == self.Estado.VERIFICADO


class DocumentoComercio(models.Model):
    """ADR-0034: PDF de evidencia (Cámara de Comercio o RUT) de una solicitud de perfil.

    Solo moderación lo ve. Al decidir el perfil se borran los bytes (`contenido = NULL`) y quedan
    tipo, tamaño, SHA-256 y fechas como constancia (Ley 1581, minimización). No se guarda el nombre
    original del archivo.
    """

    class Tipo(models.TextChoices):
        CAMARA_COMERCIO = "camara_comercio", "Certificado de Cámara de Comercio"
        RUT = "rut", "RUT"

    perfil = models.ForeignKey(PerfilComercio, on_delete=models.CASCADE, related_name="documentos")
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    contenido = models.BinaryField(null=True, editable=False)
    tamano = models.PositiveIntegerField()
    sha256 = models.CharField(max_length=64)
    subido_en = models.DateTimeField(auto_now_add=True)
    borrado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "documento de comercio"
        verbose_name_plural = "documentos de comercio"
        constraints = [
            models.UniqueConstraint(fields=["perfil", "tipo"], name="un_documento_por_tipo"),
            models.CheckConstraint(
                condition=Q(tamano__gte=1, tamano__lte=MAX_BYTES_DOCUMENTO),
                name="documento_entre_1_byte_y_2_mb",
            ),
            # Sin bytes siempre con fecha de borrado, y al revés
            models.CheckConstraint(
                condition=Q(contenido__isnull=True, borrado_en__isnull=False)
                | Q(contenido__isnull=False, borrado_en__isnull=True),
                name="documento_borrado_con_fecha",
            ),
        ]

    def __str__(self) -> str:
        estado = "borrado" if self.borrado_en else "pendiente"
        return f"{self.get_tipo_display()} · perfil {self.perfil_id} ({estado})"

    @property
    def disponible(self) -> bool:
        return self.borrado_en is None


class PrecioOficial(models.Model):
    """RF-C03: precio publicado por un comercio verificado, uno por presentación.

    `confirmado_en` es la evidencia de vigencia (30 días, ADR-003 y ADR-018): la renuevan publicar
    y la confirmación con un toque (RF-C07).
    """

    perfil = models.ForeignKey(PerfilComercio, on_delete=models.PROTECT, related_name="precios")
    presentacion = models.ForeignKey(
        "catalogo.Presentacion", on_delete=models.PROTECT, related_name="precios_oficiales"
    )
    precio = models.DecimalField(max_digits=12, decimal_places=2)
    publicado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    confirmado_en = models.DateTimeField()

    class Meta:
        verbose_name = "precio oficial"
        verbose_name_plural = "precios oficiales"
        constraints = [
            models.CheckConstraint(condition=Q(precio__gt=0), name="precio_oficial_positivo"),
            models.UniqueConstraint(
                fields=["perfil", "presentacion"], name="un_precio_oficial_por_presentacion"
            ),
        ]
        indexes = [
            models.Index(fields=["presentacion", "confirmado_en"], name="idx_oficial_presentacion")
        ]

    def __str__(self) -> str:
        return f"{self.presentacion} @ {self.perfil.establecimiento}: {self.precio} (oficial)"


class Promocion(models.Model):
    """RF-C04: promoción con reglas (ADR-014). Nunca entra en el orden de la comparación."""

    class Tipo(models.TextChoices):
        DESCUENTO_PORCENTUAL = TipoPromocion.DESCUENTO_PORCENTUAL.value, "Descuento porcentual"
        PRECIO_ESPECIAL = TipoPromocion.PRECIO_ESPECIAL.value, "Precio especial"
        PAGUE_X_LLEVE_Y = TipoPromocion.PAGUE_X_LLEVE_Y.value, "Pague X lleve Y"

    class Motivo(models.TextChoices):
        TEMPORADA = MotivoPromocion.TEMPORADA.value, "Temporada"
        LIQUIDACION = MotivoPromocion.LIQUIDACION.value, "Liquidación"
        PROXIMO_A_VENCER = MotivoPromocion.PROXIMO_A_VENCER.value, "Producto próximo a vencer"
        LANZAMIENTO = MotivoPromocion.LANZAMIENTO.value, "Lanzamiento"
        OTRO = MotivoPromocion.OTRO.value, "Otro"

    perfil = models.ForeignKey(PerfilComercio, on_delete=models.PROTECT, related_name="promociones")
    presentacion = models.ForeignKey(
        "catalogo.Presentacion", on_delete=models.PROTECT, related_name="promociones"
    )
    tipo = models.CharField(max_length=24, choices=Tipo.choices)
    porcentaje = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    precio_especial = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    pague = models.PositiveSmallIntegerField(null=True, blank=True)
    lleve = models.PositiveSmallIntegerField(null=True, blank=True)
    inicio = models.DateTimeField()
    fin = models.DateTimeField()
    motivo = models.CharField(max_length=20, choices=Motivo.choices)
    fecha_vencimiento_producto = models.DateField(null=True, blank=True)
    condiciones = models.CharField(max_length=300)
    activa = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "promoción"
        verbose_name_plural = "promociones"
        constraints = [
            models.CheckConstraint(
                condition=Q(fin__gt=models.F("inicio")), name="promo_fin_despues"
            ),
            models.CheckConstraint(
                condition=~Q(tipo="descuento_porcentual") | Q(porcentaje__gt=0, porcentaje__lt=100),
                name="promo_porcentaje_entre_0_y_100",
            ),
            models.CheckConstraint(
                condition=~Q(tipo="precio_especial") | Q(precio_especial__gt=0),
                name="promo_precio_especial_positivo",
            ),
            models.CheckConstraint(
                condition=~Q(tipo="pague_x_lleve_y") | Q(pague__gte=1, lleve__gt=models.F("pague")),
                name="promo_pague_menos_de_lo_que_lleva",
            ),
            models.CheckConstraint(
                condition=~Q(motivo="proximo_a_vencer")
                | Q(fecha_vencimiento_producto__isnull=False),
                name="promo_vencimiento_si_proximo_a_vencer",
            ),
        ]
        indexes = [
            models.Index(fields=["presentacion", "activa", "fin"], name="idx_promo_vigente"),
            models.Index(fields=["perfil", "-creado_en"], name="idx_promo_perfil"),
        ]

    def __str__(self) -> str:
        return f"{self.get_tipo_display()} · {self.presentacion} @ {self.perfil.establecimiento}"


class SolicitudCorreccion(models.Model):
    """RF-C06: el comercio pide corregir información errónea sobre su negocio."""

    class Tipo(models.TextChoices):
        DATOS_ESTABLECIMIENTO = "datos_establecimiento", "Datos del establecimiento"
        PRECIO_REPORTADO = "precio_reportado", "Un precio reportado por usuarios"
        OTRO = "otro", "Otro"

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        RESUELTA = "resuelta", "Resuelta"
        RECHAZADA = "rechazada", "No procede"

    perfil = models.ForeignKey(
        PerfilComercio, on_delete=models.PROTECT, related_name="correcciones"
    )
    tipo = models.CharField(max_length=24, choices=Tipo.choices)
    reporte = models.ForeignKey(
        "precios.ReportePrecio",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="correcciones_comercio",
    )
    descripcion = models.CharField(max_length=500)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    respuesta = models.CharField(max_length=500, blank=True)
    resuelta_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="correcciones_resueltas",
    )
    resuelta_en = models.DateTimeField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "solicitud de corrección"
        verbose_name_plural = "solicitudes de corrección"
        constraints = [
            models.CheckConstraint(
                condition=~Q(tipo="precio_reportado") | Q(reporte__isnull=False),
                name="correccion_de_precio_con_reporte",
            ),
            models.CheckConstraint(
                condition=Q(estado="pendiente")
                | Q(resuelta_por__isnull=False, resuelta_en__isnull=False),
                name="correccion_resuelta_con_moderador_y_fecha",
            ),
        ]
        indexes = [models.Index(fields=["estado", "creado_en"], name="idx_correccion_estado")]

    def __str__(self) -> str:
        return f"Corrección #{self.pk} · {self.get_tipo_display()} ({self.get_estado_display()})"
