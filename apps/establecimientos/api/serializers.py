from rest_framework import serializers

from apps.establecimientos.models import Establecimiento


class EstablecimientoSerializer(serializers.ModelSerializer):
    """Contrato público. Lista blanca: nunca sugerido_por ni revisado_por (EC-15, M-15)."""

    enlace_mapa = serializers.CharField(read_only=True, allow_null=True)

    class Meta:
        model = Establecimiento
        fields = [
            "id",
            "nombre",
            "tipo",
            "direccion",
            "barrio",
            "municipio",
            "latitud",
            "longitud",
            "enlace_mapa",
        ]
        read_only_fields = fields


class SugerenciaEntradaSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=150)
    tipo = serializers.ChoiceField(choices=Establecimiento.Tipo.choices)
    direccion = serializers.CharField(max_length=200)
    barrio = serializers.CharField(max_length=100, required=False, allow_blank=True)
    municipio = serializers.CharField(max_length=80, required=False, default="Armenia")
    latitud = serializers.DecimalField(
        max_digits=9, decimal_places=6, min_value=-90, max_value=90, required=False
    )
    longitud = serializers.DecimalField(
        max_digits=9, decimal_places=6, min_value=-180, max_value=180, required=False
    )

    def validate(self, datos):
        if ("latitud" in datos) != ("longitud" in datos):
            raise serializers.ValidationError("Envíe latitud y longitud juntas, o ninguna.")
        return datos


class SugerenciaSalidaSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    estado = serializers.CharField()
