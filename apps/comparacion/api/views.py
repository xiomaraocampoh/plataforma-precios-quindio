from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.comparacion.domain.ranking import CRITERIO_DECLARADO
from apps.comparacion.selectors import comparar_producto

from .serializers import ComparacionSerializer


class ComparacionAPI(APIView):
    """GET /api/v1/comparacion/<producto_id>/ — consulta pública (consumidor sin cuenta)."""

    permission_classes = [AllowAny]

    @extend_schema(
        responses=ComparacionSerializer,
        parameters=[OpenApiParameter("producto_id", int, OpenApiParameter.PATH)],
    )
    def get(self, request, producto_id: int):
        datos = {"criterio_orden": CRITERIO_DECLARADO, "resultados": comparar_producto(producto_id)}
        return Response(ComparacionSerializer(datos).data)
