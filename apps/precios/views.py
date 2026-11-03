from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from . import services
from .forms import RegistroPrecioForm


@login_required
@require_http_methods(["GET", "POST"])
def registrar(request):
    form = RegistroPrecioForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            reporte = services.registrar_reporte(
                autor=request.user,
                presentacion_id=d["presentacion"].pk,
                establecimiento_id=d["establecimiento"].pk,
                precio=d["precio"],
                id_cliente=d.get("id_cliente"),
            )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            return render(request, "precios/partials/_confirmacion.html", {"reporte": reporte})
    plantilla = "precios/partials/_formulario.html" if request.htmx else "precios/registrar.html"
    return render(request, plantilla, {"form": form})
