from django import forms

from apps.catalogo.models import Presentacion
from apps.establecimientos.models import Establecimiento


class RegistroPrecioForm(forms.Form):
    """Formulario mínimo para registrar en ≤ 15 s (EC-01). Validación también en servidor (M-02)."""

    establecimiento = forms.ModelChoiceField(
        queryset=Establecimiento.objects.filter(activo=True), label="¿Dónde estás?"
    )
    presentacion = forms.ModelChoiceField(
        queryset=Presentacion.objects.select_related("producto"), label="Producto y presentación"
    )
    precio = forms.DecimalField(
        min_value=1,
        max_digits=12,
        decimal_places=2,
        label="Precio en góndola ($)",
        widget=forms.NumberInput(attrs={"inputmode": "numeric", "autocomplete": "off"}),
    )
    id_cliente = forms.UUIDField(required=False, widget=forms.HiddenInput)
