from django.conf import settings
from django.db import models

from .domain.catalogo import Tipo


class CorreoPendiente(models.Model):
    """Outbox: cada correo es una fila antes de salir. Así un fallo de SMTP no pierde el correo
    y `clave_idempotencia` impide enviar dos veces el mismo evento (ADR-021).

    El contexto nunca guarda secretos (códigos, enlaces firmados): se regeneran o viajan solo en
    memoria en el primer intento.
    """

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        ENVIANDO = "enviando", "Enviando"
        ENVIADO = "enviado", "Enviado"
        FALLIDO = "fallido", "Fallido"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="correos",
    )
    destinatario = models.CharField(max_length=254, blank=True)  # vacío tras redactar (RF-03)
    tipo = models.CharField(max_length=30, choices=[(t.value, t.value) for t in Tipo])
    contexto = models.JSONField(default=dict, blank=True)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    intentos = models.PositiveSmallIntegerField(default=0)
    ultimo_intento = models.DateTimeField(null=True, blank=True)
    enviado_en = models.DateTimeField(null=True, blank=True)
    error = models.CharField(max_length=300, blank=True)
    clave_idempotencia = models.CharField(max_length=150, unique=True)
    message_id = models.CharField(max_length=200, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["creado_en", "pk"]
        indexes = [models.Index(fields=["estado", "ultimo_intento"], name="idx_correo_estado")]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(intentos__lte=3), name="correo_maximo_tres_intentos"
            ),
        ]

    def __str__(self) -> str:
        return f"Correo #{self.pk} · {self.tipo} · {self.estado}"
