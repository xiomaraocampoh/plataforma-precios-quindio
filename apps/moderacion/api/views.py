from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.moderacion import selectors, services
from apps.moderacion.permisos import EsModerador

from .serializers import (
    DecisionEntradaSerializer,
    DenunciaEntradaSerializer,
    DenunciaSalidaSerializer,
    ReporteEnRevisionSerializer,
)


class DenunciasAPI(APIView):
    """POST /api/v1/moderacion/denuncias/ — una denuncia por usuario y reporte (RF-20)."""

    permission_classes = [IsAuthenticated]
    throttle_scope = "denuncias"

    @extend_schema(request=DenunciaEntradaSerializer, responses=DenunciaSalidaSerializer)
    def post(self, request):
        entrada = DenunciaEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        d = entrada.validated_data
        try:
            denuncia = services.denunciar(
                denunciante=request.user,
                reporte_id=d["reporte"],
                motivo=d["motivo"],
                detalle=d.get("detalle", ""),
            )
        except services.DenunciaDuplicadaError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except DjangoValidationError as exc:
            raise ValidationError({"reporte": exc.messages}) from exc
        return Response(
            DenunciaSalidaSerializer({"id": denuncia.pk, "estado": denuncia.estado}).data,
            status=status.HTTP_201_CREATED,
        )


class ReportesEnRevisionAPI(ListAPIView):
    """GET /api/v1/moderacion/reportes-en-revision/ — solo moderación (RF-21)."""

    permission_classes = [EsModerador]
    serializer_class = ReporteEnRevisionSerializer

    def get_queryset(self):
        return selectors.reportes_en_revision()


class ReporteEnRevisionAPI(APIView):
    """GET/PATCH /api/v1/moderacion/reportes-en-revision/{id}/ — publicar o rechazar (RF-21)."""

    permission_classes = [EsModerador]
    throttle_scope = "moderacion"

    def _reporte(self, pk: int):
        reporte = selectors.reportes_en_revision().filter(pk=pk).first()
        if reporte is None:
            raise NotFound("No hay un reporte en revisión con ese id.")
        return reporte

    @extend_schema(responses=ReporteEnRevisionSerializer)
    def get(self, request, pk: int):
        return Response(ReporteEnRevisionSerializer(self._reporte(pk)).data)

    @extend_schema(request=DecisionEntradaSerializer, responses=ReporteEnRevisionSerializer)
    def patch(self, request, pk: int):
        reporte = self._reporte(pk)
        entrada = DecisionEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        services.decidir_reporte(
            moderador=request.user,
            reporte_id=reporte.pk,
            aprobar=entrada.validated_data["decision"] == "aprobar",
            motivo=entrada.validated_data["motivo"],
        )
        reporte.refresh_from_db()
        return Response(ReporteEnRevisionSerializer(reporte).data)
