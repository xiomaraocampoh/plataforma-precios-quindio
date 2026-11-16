from django import forms

from .models import Denuncia


class DenunciaForm(forms.Form):
    """RF-20: denunciar un precio dudoso, con motivo."""

    motivo = forms.ChoiceField(label="Motivo", choices=Denuncia.Motivo.choices)
    detalle = forms.CharField(
        label="Detalle",
        required=False,
        max_length=500,
        help_text="Opcional. Ej.: el precio real era $4.900.",
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def __init__(self, *args, reporte_id: int, **kwargs):
        super().__init__(*args, **kwargs)
        self.auto_id = f"denuncia-{reporte_id}-%s"  # ids únicos: varios formularios por página


class DecisionForm(forms.Form):
    """Decisión de la bandeja de moderación (RF-21, RF-22)."""

    TIPOS = ("reporte", "denuncia", "solicitud", "establecimiento", "usuario")

    tipo = forms.ChoiceField(choices=[(t, t) for t in TIPOS])
    objeto_id = forms.IntegerField(min_value=1)
    decision = forms.ChoiceField(choices=[("aprobar", "aprobar"), ("rechazar", "rechazar")])
    motivo = forms.CharField(required=False, max_length=500)
