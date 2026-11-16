"""Exige el segundo factor a quien lo tiene obligatorio (moderación, administración, staff).

El ingreso ya no abre la sesión sin el segundo paso, pero una sesión anterior al cambio, o de
alguien que acaba de recibir un rol con 2FA obligatoria, no lo tiene: se cierra y se pide ingresar
de nuevo. En la API se responde 401 (SessionAuthentication usa la misma sesión).
"""

from django.contrib.auth import logout
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import urlencode

from .domain.segundo_factor import segundo_factor_obligatorio
from .views.ingreso import FLAG


class SegundoFactorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario = getattr(request, "user", None)
        if usuario is not None and usuario.is_authenticated and self._falta(request, usuario):
            logout(request)
            if request.path.startswith("/api/"):
                mensaje = "Se requiere la verificación en dos pasos. Ingresa de nuevo."
                return JsonResponse({"detail": mensaje}, status=401)
            destino = reverse("cuentas:ingresar")
            return redirect(f"{destino}?{urlencode({'next': request.get_full_path()})}")
        return self.get_response(request)

    @staticmethod
    def _falta(request, usuario) -> bool:
        obligatorio = segundo_factor_obligatorio(
            rol=getattr(usuario, "rol", ""),
            es_staff=usuario.is_staff,
            es_superusuario=usuario.is_superuser,
        )
        return obligatorio and request.session.get(FLAG) != "verificado"
