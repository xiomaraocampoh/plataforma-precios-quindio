from rest_framework import serializers

from apps.catalogo.models import Presentacion, Producto


class PresentacionSerializer(serializers.ModelSerializer):
    descripcion = serializers.CharField(source="__str__", read_only=True)

    class Meta:
        model = Presentacion
        fields = ["id", "cantidad", "unidad", "codigo_barras", "descripcion"]  # lista blanca
        read_only_fields = fields


class ProductoSerializer(serializers.ModelSerializer):
    """Contrato público del catálogo (lista blanca; el catálogo no tiene datos personales)."""

    categoria = serializers.CharField(source="categoria.nombre", read_only=True)
    marca = serializers.SerializerMethodField()  # el contrato público sigue siendo texto
    presentaciones = PresentacionSerializer(many=True, read_only=True)

    def get_marca(self, producto) -> str:
        return producto.marca.nombre if producto.marca_id else ""

    class Meta:
        model = Producto
        fields = ["id", "nombre", "marca", "categoria", "presentaciones"]
        read_only_fields = fields
