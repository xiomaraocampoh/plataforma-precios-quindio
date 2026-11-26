"""Formularios del panel. Validan en el servidor lo mismo que la BD restringe (M-02)."""

import re

from django import forms

from apps.catalogo import services as catalogo
from apps.catalogo.domain.duplicados import normalizar_nombre
from apps.catalogo.domain.fotos import MAX_BYTES_SUBIDA, FotoInvalidaError
from apps.catalogo.domain.normalizacion import Unidad
from apps.catalogo.models import Categoria, Marca, Presentacion, Producto
from apps.cuentas.domain.roles import GRUPOS
from apps.cuentas.models import Usuario
from apps.establecimientos.models import Establecimiento

from . import selectors

_CODIGO = re.compile(r"^\d{8,14}$")  # EAN-8, UPC-A, EAN-13, GTIN-14


def _activos_o_actual(queryset, actual_id):
    """Opciones activas y, si el registro ya tiene una inactiva, también esa (no se pierde)."""
    filtro = {"activa": True} if "activa" in {f.name for f in queryset.model._meta.fields} else {}
    activos = queryset.filter(**filtro)
    return (activos | queryset.filter(pk=actual_id)).distinct() if actual_id else activos


class MarcaForm(forms.ModelForm):
    class Meta:
        model = Marca
        fields = ["nombre"]
        labels = {"nombre": "Nombre de la marca"}

    def clean_nombre(self):
        nombre = " ".join(self.cleaned_data["nombre"].split())
        repetida = Marca.objects.filter(nombre_normalizado=normalizar_nombre(nombre))
        if repetida.exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(
                "Ya existe una marca con ese nombre (sin contar tildes ni mayúsculas)."
            )
        return nombre


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ["nombre", "perecedera"]
        labels = {"nombre": "Nombre de la categoría", "perecedera": "Es perecedera"}
        help_texts = {"perecedera": "Sus precios vencen antes (3 días en lugar de 7)."}

    def clean_nombre(self):
        nombre = " ".join(self.cleaned_data["nombre"].split())
        repetida = Categoria.objects.filter(nombre__iexact=nombre).exclude(pk=self.instance.pk)
        if repetida.exists():
            raise forms.ValidationError("Ya existe una categoría con ese nombre.")
        return nombre


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ["nombre", "marca", "categoria", "descripcion"]
        labels = {
            "nombre": "Nombre del producto",
            "marca": "Marca",
            "categoria": "Categoría",
            "descripcion": "Descripción (opcional)",
        }
        help_texts = {
            "nombre": "Como aparece en el empaque, sin la marca. Ej.: Arroz blanco.",
            "descripcion": "Una o dos frases útiles para reconocerlo (hasta 500 caracteres). "
            "Sin precios ni mensajes comerciales.",
        }
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 3, "maxlength": 500})}

    foto = forms.FileField(
        required=False,
        label="Foto del producto",
        help_text=(
            "Arrastra la imagen aquí, pégala con Ctrl+V (o ⌘+V) tras copiarla, o busca el archivo. "
            "JPG, PNG o WebP, de hasta 5 MB y al menos 200 px. Se recorta cuadrada y se reduce "
            "sola. Usa una foto del empaque de frente, sin personas ni datos personales."
        ),
        widget=forms.FileInput(
            attrs={"accept": "image/jpeg,image/png,image/webp", "data-zona-foto": ""}
        ),
    )
    quitar_foto = forms.BooleanField(required=False, label="Quitar la foto actual")

    def clean_foto(self):
        archivo = self.cleaned_data.get("foto")
        if not archivo:
            return None
        if archivo.size > MAX_BYTES_SUBIDA:  # antes de leerla entera en memoria
            raise forms.ValidationError(f"El archivo pesa más de {MAX_BYTES_SUBIDA // 1024**2} MB.")
        try:
            return catalogo.preparar_foto(archivo.read())  # ya procesada: se valida una sola vez
        except FotoInvalidaError as exc:
            raise forms.ValidationError(str(exc)) from exc

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.foto_version:
            del self.fields["quitar_foto"]  # no hay foto que quitar
        marca = self.fields["marca"]
        marca.queryset = _activos_o_actual(Marca.objects.all(), self.instance.marca_id)
        marca.empty_label = "Sin marca"
        categoria = self.fields["categoria"]
        categoria.queryset = _activos_o_actual(
            Categoria.objects.order_by("nombre"), self.instance.categoria_id
        )
        categoria.empty_label = "Elige una"

    def clean(self):
        datos = super().clean()
        if "nombre" in datos:
            repetido = Producto.objects.filter(
                nombre_normalizado=normalizar_nombre(datos["nombre"]), marca=datos.get("marca")
            ).exclude(pk=self.instance.pk)
            if repetido.exists():
                detalle = "con esa marca" if datos.get("marca") else "sin marca"
                raise forms.ValidationError(f"Ya existe ese producto {detalle}.")
        return datos


class PresentacionForm(forms.ModelForm):
    # Opción vacía: así la fila libre no cuenta como modificada si nadie la llena
    unidad = forms.ChoiceField(
        label="Unidad", choices=[("", "Elige")] + [(u.value, u.value) for u in Unidad]
    )

    class Meta:
        model = Presentacion
        fields = ["cantidad", "unidad", "codigo_barras", "activa"]
        labels = {"cantidad": "Cantidad", "codigo_barras": "Código de barras", "activa": "Activa"}
        widgets = {
            "cantidad": forms.NumberInput(attrs={"inputmode": "decimal", "step": "any"}),
            "codigo_barras": forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "off"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:  # 500, no 500.000: en es-CO «1.000» se lee como mil
            self.initial["cantidad"] = format(self.instance.cantidad.normalize(), "f")

    def clean_cantidad(self):
        cantidad = self.cleaned_data["cantidad"]
        if cantidad is not None and cantidad <= 0:
            raise forms.ValidationError("La cantidad debe ser mayor que cero.")
        return cantidad

    def clean_codigo_barras(self):
        codigo = (self.cleaned_data.get("codigo_barras") or "").strip()
        if codigo and not _CODIGO.match(codigo):
            raise forms.ValidationError("El código de barras debe tener de 8 a 14 dígitos.")
        return codigo


class _PresentacionesFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        errores = []
        quedan = 0
        for form in self.forms:
            vacia = not form.has_changed() and not form.instance.pk  # fila extra sin llenar
            if not hasattr(form, "cleaned_data") or vacia:
                continue
            if self._should_delete_form(form):
                if form.instance.pk and not selectors.puede_eliminarse(form.instance):
                    errores.append(
                        f"La presentación {form.instance.cantidad.normalize()} "
                        f"{form.instance.unidad} tiene reportes: desactívala en lugar de quitarla."
                    )
            else:
                quedan += 1
        if not quedan:
            errores.append("El producto necesita al menos una presentación.")
        if errores:
            raise forms.ValidationError(errores)


PresentacionesFormSet = forms.inlineformset_factory(
    Producto,
    Presentacion,
    form=PresentacionForm,
    formset=_PresentacionesFormSet,
    extra=1,
    can_delete=True,
)


class EstablecimientoForm(forms.ModelForm):
    class Meta:
        model = Establecimiento
        fields = ["nombre", "tipo", "direccion", "barrio", "municipio", "latitud", "longitud"]
        labels = {"direccion": "Dirección"}
        help_texts = {
            "latitud": "Opcional. Ej.: 4.533889 (escribe ambas coordenadas o ninguna).",
            "longitud": "Opcional. Ej.: -75.681111.",
        }

    def clean(self):
        datos = super().clean()
        if (datos.get("latitud") is None) != (datos.get("longitud") is None):
            raise forms.ValidationError("Escribe la latitud y la longitud, o deja ambas vacías.")
        return datos


class RolForm(forms.Form):
    """Solo los roles con grupo; «comercio» llega con el módulo comercial (Corte III)."""

    rol = forms.ChoiceField(
        label="Rol",
        choices=[(c.value, c.label) for c in Usuario.Rol if c.value in GRUPOS],
    )
