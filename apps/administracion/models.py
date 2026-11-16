from django.conf import settings
from django.db import models


class RegistroAuditoria(models.Model):
    """Quién hizo qué y cuándo en el panel (M-14). Solo inserción: no se edita ni se borra."""

    class Accion(models.TextChoices):
        CREAR = "crear", "Crear"
        EDITAR = "editar", "Editar"
        ACTIVAR = "activar", "Activar"
        DESACTIVAR = "desactivar", "Desactivar"
        ELIMINAR = "eliminar", "Eliminar"
        ASIGNAR_ROL = "asignar_rol", "Asignar rol"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="acciones_auditadas"
    )
    accion = models.CharField(max_length=20, choices=Accion.choices)
    entidad = models.CharField(max_length=30)
    objeto_id = models.PositiveBigIntegerField()
    objeto = models.CharField(max_length=200)  # cómo se llamaba en ese momento
    cambios = models.JSONField(default=dict, blank=True)  # {"campo": [antes, después]}
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        default_permissions = ("view",)  # sin add/change/delete: la bitácora es inalterable
        ordering = ["-creado_en", "-pk"]
        indexes = [
            models.Index(fields=["-creado_en"], name="idx_auditoria_fecha"),
            models.Index(fields=["entidad", "objeto_id"], name="idx_auditoria_objeto"),
        ]

    def __str__(self) -> str:
        return f"{self.actor} · {self.get_accion_display()} {self.entidad} «{self.objeto}»"
