"""Acciones de /admin/ que delegan en servicios (RF-21, RF-22).

El admin no escribe con el ORM: cada acción llama a un servicio de moderación, que valida permisos
y registra la decisión (moderador y fecha). Así /admin/ y la bandeja dejan el mismo rastro.
"""

import unicodedata
from collections.abc import Callable

from django.contrib import admin, messages
from django.core.exceptions import ObjectDoesNotExist, ValidationError


def accion_de_moderacion(descripcion: str, servicio: Callable) -> Callable:
    """Crea una acción de admin que aplica `servicio(moderador, objeto)` a cada seleccionado."""

    @admin.action(description=descripcion)
    def accion(modeladmin, request, queryset):
        hechos, errores = 0, []
        for objeto in queryset:
            try:
                servicio(request.user, objeto)
                hechos += 1
            except (ValidationError, ValueError, PermissionError, ObjectDoesNotExist) as exc:
                errores.append(f"#{objeto.pk}: {' '.join(getattr(exc, 'messages', [str(exc)]))}")
        if hechos:
            modeladmin.message_user(request, f"{descripcion}: {hechos} hecho(s).")
        for error in errores:
            modeladmin.message_user(request, error, level=messages.WARNING)

    ascii_ = unicodedata.normalize("NFKD", descripcion.lower()).encode("ascii", "ignore").decode()
    accion.__name__ = "accion_" + "".join(c if c.isalnum() else "_" for c in ascii_)
    return accion
