import re

from django import forms

from . import services
from .domain.normalizacion import Unidad
from .models import Categoria

_CODIGO = re.compile(r"^\d{8,14}$")


class SolicitudForm(forms.Form):
    """RF-06: solicitar un producto o una presentación que no está en el catálogo."""

    nombre = forms.CharField(
        label="Nombre del producto",
        max_length=150,
        help_text="Como aparece en el empaque, sin la marca. Ej.: Arroz blanco.",
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
    marca = forms.CharField(label="Marca", max_length=80, required=False)
    categoria = forms.ModelChoiceField(
        label="Categoría", queryset=Categoria.objects.order_by("nombre"), empty_label="Elige una"
    )
    cantidad = forms.DecimalField(
        label="Cantidad",
        min_value=0.001,
        max_digits=10,
        decimal_places=3,
        help_text="Solo el número. Ej.: 500.",
        widget=forms.NumberInput(attrs={"inputmode": "decimal", "step": "any"}),
    )
    unidad = forms.ChoiceField(label="Unidad", choices=[(u.value, u.value) for u in Unidad])
    codigo_barras = forms.CharField(
        label="Código de barras",
        required=False,
        max_length=14,
        help_text="Los números bajo las barras (8 a 14 dígitos).",
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "off"}),
    )
    detalle = forms.CharField(
        label="Algo más que debamos saber",
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def clean_codigo_barras(self):
        codigo = self.cleaned_data["codigo_barras"].strip()
        if codigo and not _CODIGO.match(codigo):
            raise forms.ValidationError("El código de barras debe tener de 8 a 14 dígitos.")
        return codigo

    def clean(self):
        datos = super().clean()
        if {"nombre", "cantidad", "unidad"} <= datos.keys() and services.existe_presentacion(
            nombre=datos["nombre"],
            marca=datos.get("marca", ""),
            cantidad=datos["cantidad"],
            unidad=datos["unidad"],
        ):
            raise forms.ValidationError(
                "Esa presentación ya está en el catálogo. Búscala en Productos."
            )
        return datos
