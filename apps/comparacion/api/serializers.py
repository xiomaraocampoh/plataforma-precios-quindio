from rest_framework import serializers


class ResultadoComparacionSerializer(serializers.Serializer):
    """Contrato público. Lista blanca de campos: NUNCA autor ni ubicación del reportante (M-15)."""

    establecimiento_id = serializers.IntegerField()
    establecimiento = serializers.CharField()
    presentacion = serializers.CharField()
    precio = serializers.DecimalField(max_digits=12, decimal_places=2)
    precio_unitario = serializers.DecimalField(max_digits=14, decimal_places=2)
    unidad_base = serializers.CharField()
    fuente = serializers.CharField()
    confianza = serializers.CharField()
    fecha_observacion = serializers.DateTimeField()
    es_promocion = serializers.BooleanField()


class ComparacionSerializer(serializers.Serializer):
    criterio_orden = serializers.CharField()
    resultados = ResultadoComparacionSerializer(many=True)
