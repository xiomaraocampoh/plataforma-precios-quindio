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
    # Aditivo en /v1 (ADR-018): precio que reportan los usuarios cuando difiere del oficial
    usuarios_reportan = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)


class PromocionPublicaSerializer(serializers.Serializer):
    """Aditivo en /v1 (ADR-014, decisión D-3). Lista blanca: las condiciones de la promoción y el
    establecimiento, NUNCA el perfil, el usuario ni el contacto del comercio (M-15)."""

    establecimiento_id = serializers.IntegerField()
    establecimiento = serializers.CharField()
    presentacion = serializers.CharField()
    tipo = serializers.CharField()
    descripcion = serializers.CharField()
    precio_efectivo = serializers.DecimalField(max_digits=12, decimal_places=2)
    precio_efectivo_unitario = serializers.DecimalField(max_digits=14, decimal_places=2)
    unidad_base = serializers.CharField()
    inicio = serializers.DateTimeField()
    fin = serializers.DateTimeField()
    motivo = serializers.CharField()
    condiciones = serializers.CharField()
    fecha_vencimiento_producto = serializers.DateField(allow_null=True)


class ComparacionSerializer(serializers.Serializer):
    criterio_orden = serializers.CharField()
    resultados = ResultadoComparacionSerializer(many=True)
    # Las promociones viajan aparte, como la referencia SIPSA: nunca alteran el orden (EC-06)
    promociones = PromocionPublicaSerializer(many=True)
