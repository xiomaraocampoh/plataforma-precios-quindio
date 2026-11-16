"""Sincroniza el grupo de Django con Usuario.rol después de guardar (rol = fuente de verdad)."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Usuario
from .services import sincronizar_grupo_de_rol


@receiver(post_save, sender=Usuario, dispatch_uid="cuentas_sincronizar_grupo_de_rol")
def _sincronizar_grupo(sender, instance, created, update_fields=None, **kwargs):
    # Un login solo actualiza last_login: no hace falta tocar los grupos
    if created or update_fields is None or "rol" in update_fields:
        sincronizar_grupo_de_rol(instance)
