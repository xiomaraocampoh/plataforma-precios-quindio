from django import forms

from apps.catalogo import selectors as catalogo
from apps.catalogo.domain.normalizacion import formatear_cantidad
from apps.catalogo.models import Presentacion
from apps.establecimientos.models import Establecimiento


class _ConDatosDeUnidad:
    """Cada opción lleva su cantidad y unidad para calcular en vivo el precio por unidad (RF-16).

    Es solo una ayuda visual: el precio por unidad que se guarda y se compara lo calcula siempre
    el dominio (`precio_por_unidad`) en el servidor.
    """

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        opcion = super().create_option(name, value, label, selected, index, subindex, attrs)
        instancia = getattr(value, "instance", None)
        if instancia is not None:
            opcion["attrs"]["data-cantidad"] = format(instancia.cantidad.normalize(), "f")
            opcion["attrs"]["data-unidad"] = instancia.unidad
        return opcion


class SelectPresentacion(_ConDatosDeUnidad, forms.Select):
    """Lista completa: solo si no se sabe de qué producto es (p. ej. reenvíos de la cola)."""


class BotonesPresentacion(_ConDatosDeUnidad, forms.RadioSelect):
    """Las presentaciones de UN producto, como botones: elegir cuesta un toque, no una lista."""


class _PresentacionCampo(forms.ModelChoiceField):
    def __init__(self, *args, corta: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self._corta = corta

    def label_from_instance(self, obj):
        if self._corta:  # el producto ya está en el título: basta «500 g»
            return f"{formatear_cantidad(obj.cantidad)} {obj.unidad}"
        return super().label_from_instance(obj)


class RegistroPrecioForm(forms.Form):
    """Formulario mínimo para registrar en ≤ 15 s (EC-01). Validación también en servidor (M-02).

    Con `producto`, solo ofrece las presentaciones de ese producto (PUX-01: el selector con todo
    el catálogo fue lo más difícil) y pone el foco en el primer dato que falte.
    """

    establecimiento = forms.ModelChoiceField(
        queryset=Establecimiento.objects.filter(activo=True), label="¿Dónde estás?"
    )
    presentacion = _PresentacionCampo(
        queryset=Presentacion.objects.none(),
        label="Producto y presentación",
        widget=SelectPresentacion,
    )
    precio = forms.DecimalField(
        min_value=1,
        max_digits=12,
        decimal_places=2,
        label="Precio total del empaque ($)",
        help_text="El precio que marca la etiqueta para esa presentación",
        widget=forms.NumberInput(
            attrs={"inputmode": "numeric", "autocomplete": "off", "data-precio-total": ""}
        ),
    )
    # Registro sin conexión (ADR-009): la cola del navegador reenvía con el mismo id y la hora
    # en que se vio el precio; el servicio aplica RN-08 a esa fecha.
    id_cliente = forms.UUIDField(required=False, widget=forms.HiddenInput)
    fecha_observacion = forms.DateTimeField(required=False, widget=forms.HiddenInput)

    field_order = ["presentacion", "establecimiento", "precio"]

    def __init__(self, *args, producto=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.producto = producto
        # Solo lo que sigue en el catálogo: presentación, producto y categoría activos
        presentaciones = catalogo.presentaciones_publicas().select_related("producto__marca")
        campo = self.fields["presentacion"]
        if producto is not None:
            presentaciones = presentaciones.filter(producto=producto).order_by("unidad", "cantidad")
            campo.widget = BotonesPresentacion()
            campo.label = "Presentación"
            campo._corta = True
            campo.empty_label = None  # botones: sin la opción vacía «---------»
        campo.queryset = presentaciones
        if not self.is_bound:
            self._enfocar_primer_dato_pendiente()

    def _enfocar_primer_dato_pendiente(self) -> None:
        """Con todo precargado, el cursor cae en el precio: lo único que falta escribir."""
        if self.initial.get("presentacion") is None:
            return  # los botones de presentación están a la vista: no hay un campo donde enfocar
        pendiente = "precio" if self.initial.get("establecimiento") else "establecimiento"
        self.fields[pendiente].widget.attrs["autofocus"] = True
