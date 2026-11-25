"""Quién puede usar el portal de comercios y quién verifica (ADR-015).

El criterio de moderación es el mismo de `moderacion.permisos.es_moderador` (rol moderador o
administrador, o personal). Se repite aquí en vez de importarlo porque entre módulos solo se
importan servicios, selectores, dominio o modelos (CLAUDE.md §3). Los moderadores ya pasan por la
verificación en dos pasos obligatoria (RF-27, `cuentas.middleware`).
"""

from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

ROLES_MODERACION = frozenset({"moderador", "administrador"})


def es_moderador(usuario) -> bool:
    return bool(
        usuario
        and usuario.is_authenticated
        and usuario.is_active
        and (usuario.is_staff or getattr(usuario, "rol", "") in ROLES_MODERACION)
    )


def es_comercio(usuario) -> bool:
    return bool(
        usuario
        and usuario.is_authenticated
        and usuario.is_active
        and getattr(usuario, "rol", "") == "comercio"
    )


def _exigir_moderador(usuario) -> bool:
    if not usuario.is_authenticated:
        return False  # redirige al ingreso
    if es_moderador(usuario):
        return True
    raise PermissionDenied("Solo moderación puede ver esta página.")


solo_moderadores = user_passes_test(_exigir_moderador)


class EsComercio(BasePermission):
    """API: rol comercio. Que el perfil esté verificado lo exige además cada servicio."""

    message = "Solo un comercio puede usar este recurso."

    def has_permission(self, request, view) -> bool:
        return es_comercio(request.user)
