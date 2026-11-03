from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.precios import services

from .serializers import ReportePrecioEntradaSerializer, ReportePrecioSalidaSerializer


class RegistrarReporteAPI(APIView):
    """POST /api/v1/precios/reportes/ — solo usuarios autenticados (M-13)."""

    permission_classes = [IsAuthenticated]
    throttle_scope = "reportes"

    @extend_schema(request=ReportePrecioEntradaSerializer, responses=ReportePrecioSalidaSerializer)
    def post(self, request):
        entrada = ReportePrecioEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        d = entrada.validated_data
        try:
            reporte = services.registrar_reporte(
                autor=request.user,
                presentacion_id=d["presentacion"],
                establecimiento_id=d["establecimiento"],
                precio=d["precio"],
                fecha_observacion=d.get("fecha_observacion"),
                id_cliente=d.get("id_cliente"),
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict) from exc
        return Response(ReportePrecioSalidaSerializer(reporte).data, status=status.HTTP_201_CREATED)
