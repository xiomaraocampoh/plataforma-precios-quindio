"""API de comercios (/api/v1/comercios/). M-13: autenticación, rol comercio y `throttle_scope`.

Un comercio solo ve y edita lo suyo: cada consulta parte de su propio perfil y los servicios
rechazan lo ajeno. Que el perfil esté verificado lo exige cada servicio (ADR-015).
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, Throttled, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .. import selectors, services
from ..permisos import EsComercio
from .serializers import (
    ConfirmacionSalidaSerializer,
    PerfilSalidaSerializer,
    PrecioOficialEntradaSerializer,
    PrecioOficialSalidaSerializer,
    PromocionEntradaSerializer,
    PromocionSalidaSerializer,
)


class _ComercioAPI(APIView):
    permission_classes = [IsAuthenticated, EsComercio]
    throttle_scope = "comercios"

    def perfil(self):
        perfil = selectors.perfil_de(self.request.user)
        if perfil is None:
            raise NotFound("No tienes un perfil de comercio.")
        return perfil

    @staticmethod
    def ejecutar(funcion, **datos):
        try:
            return funcion(**datos)
        except services.LimiteComercioError as exc:
            raise Throttled(detail=str(exc)) from exc
        except DjangoValidationError as exc:
            raise ValidationError({"detalle": exc.messages}) from exc


class PerfilAPI(_ComercioAPI):
    """GET /api/v1/comercios/perfil/ — el perfil propio y su estado."""

    @extend_schema(responses=PerfilSalidaSerializer)
    def get(self, request):
        return Response(PerfilSalidaSerializer(self.perfil()).data)


class PreciosOficialesAPI(_ComercioAPI):
    """GET: sus precios oficiales. POST: publica o actualiza uno (RF-C03, 30 días)."""

    @extend_schema(responses=PrecioOficialSalidaSerializer(many=True))
    def get(self, request):
        precios = self.perfil().precios.order_by("presentacion_id")
        return Response(PrecioOficialSalidaSerializer(precios, many=True).data)

    @extend_schema(request=PrecioOficialEntradaSerializer, responses=PrecioOficialSalidaSerializer)
    def post(self, request):
        entrada = PrecioOficialEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        oficial = self.ejecutar(
            services.publicar_precio_oficial,
            usuario=request.user,
            presentacion_id=entrada.validated_data["presentacion"],
            precio=entrada.validated_data["precio"],
        )
        return Response(PrecioOficialSalidaSerializer(oficial).data, status=status.HTTP_201_CREATED)


class ConfirmarVigenciaAPI(_ComercioAPI):
    """POST /api/v1/comercios/precios/confirmar/ — RF-C07, un toque."""

    @extend_schema(request=None, responses=ConfirmacionSalidaSerializer)
    def post(self, request):
        n = self.ejecutar(services.confirmar_vigencia, usuario=request.user)
        return Response(ConfirmacionSalidaSerializer({"renovados": n}).data)


class PromocionesAPI(_ComercioAPI):
    """GET: sus promociones. POST: crea una (RF-C04, ADR-014)."""

    @extend_schema(responses=PromocionSalidaSerializer(many=True))
    def get(self, request):
        promociones = self.perfil().promociones.order_by("-creado_en")
        return Response(PromocionSalidaSerializer(promociones, many=True).data)

    @extend_schema(request=PromocionEntradaSerializer, responses=PromocionSalidaSerializer)
    def post(self, request):
        entrada = PromocionEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        d = dict(entrada.validated_data)
        d["presentacion_id"] = d.pop("presentacion")
        promocion = self.ejecutar(services.crear_promocion, usuario=request.user, **d)
        return Response(PromocionSalidaSerializer(promocion).data, status=status.HTTP_201_CREATED)


class TerminarPromocionAPI(_ComercioAPI):
    """POST /api/v1/comercios/promociones/<id>/terminar/ — solo una promoción propia."""

    @extend_schema(request=None, responses=PromocionSalidaSerializer)
    def post(self, request, promocion_id: int):
        promocion = self.ejecutar(
            services.finalizar_promocion, usuario=request.user, promocion_id=promocion_id
        )
        return Response(PromocionSalidaSerializer(promocion).data)
