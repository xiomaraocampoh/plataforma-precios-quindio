"""POST /interno/correos/procesar/: reintentos del outbox sin worker (ADR-021).

Render gratuito no tiene procesos en segundo plano: un cron externo (GitHub Actions, cada 10 min)
llama este endpoint con `Authorization: Bearer <CORREO_CRON_TOKEN>`. Corre una pasada de
`enviar_correos` con un tope y devuelve solo conteos. Sin sesión ni CSRF (no usa cookies), con
throttle propio. Sin token configurado, siempre responde 403.
"""

import hmac

from django.conf import settings
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
    throttle_classes,
)
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from . import services


class TieneTokenDeCron(BasePermission):
    message = "Token inválido."

    def has_permission(self, request, view) -> bool:
        esperado = settings.CORREO_CRON_TOKEN
        cabecera = request.headers.get("Authorization", "")
        recibido = (
            cabecera.removeprefix("Bearer ").strip() if cabecera.startswith("Bearer ") else ""
        )
        if not esperado or not recibido:
            return False
        return hmac.compare_digest(recibido.encode(), esperado.encode())


@api_view(["POST"])
@authentication_classes([])
@permission_classes([TieneTokenDeCron])
@throttle_classes([ScopedRateThrottle])
def procesar_correos(request):
    resumen = services.enviar_pendientes(limite=settings.CORREOS_POR_PASADA)
    return Response(resumen)


procesar_correos.cls.throttle_scope = "correos_cron"
procesar_correos.cls.schema = None  # interno: fuera de la documentación OpenAPI
