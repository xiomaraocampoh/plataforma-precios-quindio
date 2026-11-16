"""Quién modera (RF-21): rol moderador o personal (is_staff), con la cuenta activa."""

from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission


def es_moderador(usuario) -> bool:
    return bool(
        usuario
        and usuario.is_authenticated
        and usuario.is_active
        and (usuario.is_staff or getattr(usuario, "rol", "") == "moderador")
    )


def _exigir(usuario) -> bool:
    if not usuario.is_authenticated:
        return False  # redirige al ingreso
    if es_moderador(usuario):
        return True
    raise PermissionDenied("Solo moderación puede ver esta página.")


solo_moderadores = user_passes_test(_exigir)


class EsModerador(BasePermission):
    message = "Solo moderación puede usar este recurso."

    def has_permission(self, request, view) -> bool:
        return es_moderador(request.user)
