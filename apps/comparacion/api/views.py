from dataclasses import asdict

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.comparacion.domain.ranking import CRITERIO_DECLARADO
from apps.comparacion.selectors import FilaComparacion, comparar_filas

from .serializers import ComparacionSerializer


def _publico(fila: FilaComparacion) -> dict:
    """El resultado más los datos públicos del comercio; el serializer filtra por lista blanca."""
    return {
        **asdict(fila.resultado),
        "establecimiento_tipo": fila.tipo,
        "direccion": fila.direccion,
        "barrio": fila.barrio,
        "municipio": fila.municipio,
    }


class ComparacionAPI(APIView):
    """GET /api/v1/comparacion/<producto_id>/ — consulta pública (consumidor sin cuenta)."""

    permission_classes = [AllowAny]

    @extend_schema(
        responses=ComparacionSerializer,
        parameters=[OpenApiParameter("producto_id", int, OpenApiParameter.PATH)],
    )
    def get(self, request, producto_id: int):
        resultados = [_publico(f) for f in comparar_filas(producto_id)]  # orden neutral (EC-06)
        datos = {"criterio_orden": CRITERIO_DECLARADO, "resultados": resultados}
        return Response(ComparacionSerializer(datos).data)
