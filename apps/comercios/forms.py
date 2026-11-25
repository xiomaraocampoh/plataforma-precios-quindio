"""Formularios del portal de comercios. Validan la forma; las reglas viven en services y domain.

Cada control tiene etiqueta (se pinta con templates/partials/_campo.html) y los límites también
están en la BD (CHECK y UNIQUE de models.py).
"""

from datetime import datetime, time, timedelta
from decimal import Decimal

from django import forms
from django.utils import timezone

from apps.catalogo import selectors as catalogo
from apps.establecimientos.models import Establecimiento

from .models import PerfilComercio, Promocion, SolicitudCorreccion

PRECIO_MAXIMO = Decimal("2000000")


def inicio_del_dia(dia) -> datetime:
    return timezone.make_aware(datetime.combine(dia, time.min))


class PerfilForm(forms.Form):
    establecimiento = forms.ModelChoiceField(
        label="Tu establecimiento",
        queryset=Establecimiento.objects.none(),
        help_text="Si no aparece, primero sugiérelo en el directorio.",
    )
    nombre_contacto = forms.CharField(label="Nombre de quien atiende el perfil", max_length=120)
    telefono = forms.CharField(
        label="Teléfono de contacto",
        max_length=20,
        required=False,
        help_text="Solo lo ve moderación. Nunca se publica.",
    )
    evidencia = forms.CharField(
        label="Evidencia de que representas al comercio",
        max_length=300,
        help_text="NIT o RUT, o cuéntanos cómo enviarás la foto de la fachada con tu código.",
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ocupados = PerfilComercio.objects.exclude(estado=PerfilComercio.Estado.RECHAZADO)
        self.fields["establecimiento"].queryset = (
            Establecimiento.objects.filter(activo=True, estado=Establecimiento.Estado.APROBADO)
            .exclude(pk__in=ocupados.values("establecimiento_id"))
            .order_by("nombre")
        )


class _PresentacionField(forms.ModelChoiceField):
    def label_from_instance(self, obj) -> str:
        marca = f" {obj.producto.marca.nombre}" if obj.producto.marca_id else ""
        return f"{obj.producto.nombre}{marca} · {obj}"


class PrecioOficialForm(forms.Form):
    presentacion = _PresentacionField(
        label="Producto y presentación", queryset=catalogo.presentaciones_publicas().none()
    )
    precio = forms.DecimalField(
        label="Precio de venta (en pesos)",
        min_value=Decimal("1"),
        max_value=PRECIO_MAXIMO,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"inputmode": "numeric", "step": "1"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["presentacion"].queryset = (
            catalogo.presentaciones_publicas()
            .select_related("producto__marca")
            .order_by("producto__nombre", "cantidad")
        )


class PromocionForm(forms.Form):
    presentacion = _PresentacionField(
        label="Producto con precio oficial", queryset=catalogo.presentaciones_publicas().none()
    )
    tipo = forms.ChoiceField(label="Tipo de promoción", choices=Promocion.Tipo.choices)
    porcentaje = forms.DecimalField(
        label="Porcentaje de descuento",
        required=False,
        min_value=Decimal("0.01"),
        max_value=Decimal("99.99"),
        decimal_places=2,
        help_text="Solo para «Descuento porcentual». Mayor que 0 y menor que 100.",
    )
    precio_especial = forms.DecimalField(
        label="Precio especial (en pesos)",
        required=False,
        min_value=Decimal("1"),
        max_value=PRECIO_MAXIMO,
        decimal_places=2,
        help_text="Solo para «Precio especial». Debe ser menor que tu precio oficial.",
    )
    lleve = forms.IntegerField(
        label="Lleve (unidades)", required=False, min_value=2, max_value=20, help_text="Ej.: 3"
    )
    pague = forms.IntegerField(
        label="Pague (unidades)", required=False, min_value=1, max_value=19, help_text="Ej.: 2"
    )
    inicio = forms.DateField(label="Desde", widget=forms.DateInput(attrs={"type": "date"}))
    fin = forms.DateField(
        label="Hasta (inclusive)",
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text="La promoción termina al final de este día.",
    )
    motivo = forms.ChoiceField(label="Motivo", choices=Promocion.Motivo.choices)
    fecha_vencimiento_producto = forms.DateField(
        label="Fecha de vencimiento del producto",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text="Obligatoria si el motivo es «Producto próximo a vencer».",
    )
    condiciones = forms.CharField(
        label="Condiciones",
        max_length=300,
        help_text="Se muestran junto al precio. Ej.: «Hasta agotar existencias».",
    )

    def __init__(self, *args, perfil=None, **kwargs):
        super().__init__(*args, **kwargs)
        presentaciones = catalogo.presentaciones_publicas().select_related("producto__marca")
        if perfil is not None:
            presentaciones = presentaciones.filter(precios_oficiales__perfil=perfil)
        self.fields["presentacion"].queryset = presentaciones.order_by("producto__nombre")

    def clean(self):
        datos = super().clean()
        if datos.get("inicio") and datos.get("fin") and datos["fin"] < datos["inicio"]:
            self.add_error("fin", "La fecha final no puede ser anterior a la inicial.")
        return datos

    def datos_para_servicio(self) -> dict:
        d = self.cleaned_data
        return {
            "presentacion_id": d["presentacion"].pk,
            "tipo": d["tipo"],
            "porcentaje": d.get("porcentaje"),
            "precio_especial": d.get("precio_especial"),
            "pague": d.get("pague"),
            "lleve": d.get("lleve"),
            "inicio": inicio_del_dia(d["inicio"]),
            "fin": inicio_del_dia(d["fin"] + timedelta(days=1)),
            "motivo": d["motivo"],
            "condiciones": d["condiciones"],
            "fecha_vencimiento_producto": d.get("fecha_vencimiento_producto"),
        }


class CorreccionForm(forms.Form):
    tipo = forms.ChoiceField(
        label="¿Qué quieres corregir?", choices=SolicitudCorreccion.Tipo.choices
    )
    reporte = forms.TypedChoiceField(
        label="Precio reportado",
        required=False,
        coerce=int,
        empty_value=None,
        help_text="Solo si elegiste «Un precio reportado por usuarios».",
    )
    descripcion = forms.CharField(
        label="Qué está mal y cuál es el dato correcto",
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, reportes=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["reporte"].choices = [("", "Ninguno")] + [
            (
                r.pk,
                f"{r.presentacion.producto.nombre} {r.presentacion} · ${r.precio:,.0f}".replace(
                    ",", "."
                )
                + f" · {timezone.localtime(r.fecha_observacion):%d/%m/%Y}",
            )
            for r in reportes
        ]


class DecisionForm(forms.Form):
    decision = forms.ChoiceField(choices=[("aprobar", "Aprobar"), ("rechazar", "Rechazar")])
    motivo = forms.CharField(label="Motivo o respuesta", max_length=300, required=False)
