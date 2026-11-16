from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.establecimientos import selectors, services

from .serializers import (
    EstablecimientoSerializer,
    SugerenciaEntradaSerializer,
    SugerenciaSalidaSerializer,
)


@extend_schema(parameters=[OpenApiParameter("municipio", str), OpenApiParameter("barrio", str)])
class EstablecimientosAPI(ListAPIView):
    """GET /api/v1/establecimientos/?municipio=&barrio= — directorio público (RF-08)."""

    permission_classes = [AllowAny]
    serializer_class = EstablecimientoSerializer

    def get_queryset(self):
        p = self.request.query_params
        return selectors.directorio(municipio=p.get("municipio", ""), barrio=p.get("barrio", ""))


class SugerenciaEstablecimientoAPI(APIView):
    """POST /api/v1/establecimientos/sugerencias/ — queda pendiente de moderación (RF-10)."""

    permission_classes = [IsAuthenticated]
    throttle_scope = "sugerencias"

    @extend_schema(request=SugerenciaEntradaSerializer, responses=SugerenciaSalidaSerializer)
    def post(self, request):
        entrada = SugerenciaEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        e = services.sugerir_establecimiento(autor=request.user, **entrada.validated_data)
        return Response(
            SugerenciaSalidaSerializer({"id": e.pk, "estado": e.estado}).data,
            status=status.HTTP_201_CREATED,
        )
