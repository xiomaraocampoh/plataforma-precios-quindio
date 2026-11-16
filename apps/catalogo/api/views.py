from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import NotFound
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny

from apps.catalogo import selectors

from .serializers import ProductoSerializer


@extend_schema(
    parameters=[
        OpenApiParameter(
            "q", str, description="Nombre (sin tildes ni mayúsculas) o código de barras"
        )
    ]
)
class ProductosAPI(ListAPIView):
    """GET /api/v1/catalogo/productos/?q= — búsqueda pública del catálogo (RF-04)."""

    permission_classes = [AllowAny]
    serializer_class = ProductoSerializer

    def get_queryset(self):
        return selectors.listar_productos(texto=self.request.query_params.get("q", ""))


class ProductoAPI(RetrieveAPIView):
    """GET /api/v1/catalogo/productos/{id}/ — un producto con sus presentaciones (RF-06)."""

    permission_classes = [AllowAny]
    serializer_class = ProductoSerializer

    def get_object(self):
        producto = selectors.obtener_producto(self.kwargs["pk"])
        if producto is None:
            raise NotFound("El producto no existe.")
        return producto
