from rest_framework import serializers


class ResultadoComparacionSerializer(serializers.Serializer):
    """Contrato público. Lista blanca de campos: NUNCA autor ni ubicación del reportante (M-15).

    La dirección es la del COMERCIO, un dato público del directorio (RF-16, EC-15); no la de
    quien reportó.
    """

    establecimiento_id = serializers.IntegerField()
    establecimiento = serializers.CharField()
    establecimiento_tipo = serializers.CharField()
    direccion = serializers.CharField()
    barrio = serializers.CharField()
    municipio = serializers.CharField()
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
