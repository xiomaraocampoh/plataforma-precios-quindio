"""Contratos de la API de comercios. Lista blanca de campos: nunca `fields = "__all__"`.

El comercio solo ve lo suyo. Ni aquí ni en la API pública sale el usuario, el teléfono, la
evidencia ni quién verificó el perfil (Ley 1581, M-15).
"""

from decimal import Decimal

from rest_framework import serializers

from ..models import Promocion


class PerfilSalidaSerializer(serializers.Serializer):
    establecimiento_id = serializers.IntegerField()
    establecimiento = serializers.CharField(source="establecimiento.nombre")
    estado = serializers.CharField()
    verificado_en = serializers.DateTimeField(allow_null=True)


class PrecioOficialEntradaSerializer(serializers.Serializer):
    presentacion = serializers.IntegerField(min_value=1)
    precio = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("1"), max_value=Decimal("2000000")
    )


class PrecioOficialSalidaSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    presentacion = serializers.IntegerField(source="presentacion_id")
    precio = serializers.DecimalField(max_digits=12, decimal_places=2)
    confirmado_en = serializers.DateTimeField()


class PromocionEntradaSerializer(serializers.Serializer):
    presentacion = serializers.IntegerField(min_value=1)
    tipo = serializers.ChoiceField(choices=Promocion.Tipo.choices)
    porcentaje = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    precio_especial = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    pague = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=19)
    lleve = serializers.IntegerField(required=False, allow_null=True, min_value=2, max_value=20)
    inicio = serializers.DateTimeField()
    fin = serializers.DateTimeField()
    motivo = serializers.ChoiceField(choices=Promocion.Motivo.choices)
    condiciones = serializers.CharField(max_length=300)
    fecha_vencimiento_producto = serializers.DateField(required=False, allow_null=True)


class PromocionSalidaSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    presentacion = serializers.IntegerField(source="presentacion_id")
    tipo = serializers.CharField()
    porcentaje = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    precio_especial = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    pague = serializers.IntegerField(allow_null=True)
    lleve = serializers.IntegerField(allow_null=True)
    inicio = serializers.DateTimeField()
    fin = serializers.DateTimeField()
    motivo = serializers.CharField()
    condiciones = serializers.CharField()
    fecha_vencimiento_producto = serializers.DateField(allow_null=True)
    activa = serializers.BooleanField()


class ConfirmacionSalidaSerializer(serializers.Serializer):
    renovados = serializers.IntegerField()
