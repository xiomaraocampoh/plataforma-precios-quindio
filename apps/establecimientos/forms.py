from django import forms

from .models import Establecimiento


class SugerenciaForm(forms.Form):
    """RF-10: sugerir un establecimiento que no está en el directorio."""

    nombre = forms.CharField(label="Nombre del establecimiento", max_length=150)
    tipo = forms.ChoiceField(label="Tipo", choices=Establecimiento.Tipo.choices)
    direccion = forms.CharField(
        label="Dirección",
        max_length=200,
        help_text="Ej.: Cra 14 # 10-20.",
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
    barrio = forms.CharField(label="Barrio", max_length=100, required=False)
    municipio = forms.CharField(label="Municipio", max_length=80, initial="Armenia")
    latitud = forms.DecimalField(
        label="Latitud",
        required=False,
        min_value=-90,
        max_value=90,
        max_digits=9,
        decimal_places=6,
        help_text="Opcional. En OpenStreetMap: clic derecho sobre el lugar → «Mostrar dirección».",
        widget=forms.NumberInput(attrs={"step": "any", "inputmode": "decimal"}),
    )
    longitud = forms.DecimalField(
        label="Longitud",
        required=False,
        min_value=-180,
        max_value=180,
        max_digits=9,
        decimal_places=6,
        widget=forms.NumberInput(attrs={"step": "any", "inputmode": "decimal"}),
    )

    def clean(self):
        datos = super().clean()
        if (datos.get("latitud") is None) != (datos.get("longitud") is None):
            raise forms.ValidationError("Escribe la latitud y la longitud juntas, o ninguna.")
        return datos
