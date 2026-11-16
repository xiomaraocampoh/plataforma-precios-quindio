from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_http_methods

from . import selectors, services
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
        except services.LimiteDeRegistrosExcedidoError as exc:
            form.add_error(None, str(exc))  # RN-10
        else:
            return render(request, "precios/partials/_confirmacion.html", {"reporte": reporte})
    plantilla = "precios/partials/_formulario.html" if request.htmx else "precios/registrar.html"
    return render(request, plantilla, {"form": form})


@login_required
@require_GET
def mis_aportes(request):
    """Lista de los reportes del usuario con su estado (prioridad C)."""
    pagina = Paginator(selectors.listar_aportes(request.user), 20).get_page(
        request.GET.get("pagina")
    )
    return render(request, "precios/mis_aportes.html", {"pagina": pagina})
