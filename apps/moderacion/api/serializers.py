from rest_framework import serializers

from apps.moderacion.models import Denuncia
from apps.precios.models import ReportePrecio


class DenunciaEntradaSerializer(serializers.Serializer):
    reporte = serializers.IntegerField(min_value=1)
    motivo = serializers.ChoiceField(choices=Denuncia.Motivo.choices)
    detalle = serializers.CharField(max_length=500, required=False, allow_blank=True)


class DenunciaSalidaSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    estado = serializers.CharField()


class ReporteEnRevisionSerializer(serializers.ModelSerializer):
    """Lista blanca: NUNCA el autor, ni siquiera para moderación por API (EC-07, M-15)."""

    presentacion = serializers.CharField(source="presentacion.__str__", read_only=True)
    establecimiento = serializers.CharField(source="establecimiento.nombre", read_only=True)

    class Meta:
        model = ReportePrecio
        fields = [
            "id",
            "presentacion",
            "establecimiento",
            "precio",
            "fecha_observacion",
            "creado_en",
            "estado",
        ]
        read_only_fields = fields


class DecisionEntradaSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["aprobar", "rechazar"])
    motivo = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
