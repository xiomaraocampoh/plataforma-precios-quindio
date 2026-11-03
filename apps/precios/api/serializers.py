from rest_framework import serializers

from apps.precios.models import ReportePrecio


class ReportePrecioEntradaSerializer(serializers.Serializer):
    presentacion = serializers.IntegerField(min_value=1)
    establecimiento = serializers.IntegerField(min_value=1)
    precio = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=1)
    fecha_observacion = serializers.DateTimeField(required=False)
    id_cliente = serializers.UUIDField(required=False)


class ReportePrecioSalidaSerializer(serializers.ModelSerializer):
    """Respuesta al propio reportante. No incluye datos de otros usuarios."""

    class Meta:
        model = ReportePrecio
        fields = ["id", "presentacion", "establecimiento", "precio", "estado", "fecha_observacion"]
        read_only_fields = fields
