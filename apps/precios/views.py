from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

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
                fecha_observacion=d.get("fecha_observacion"),
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


@login_required
@require_POST
def sigue_igual(request, reporte_id: int):
    """RF-14: botón «Sigue igual» (HTMX). Responde con el estado del botón."""
    contexto = {"reporte_id": reporte_id, "confirmado": False, "mensaje": ""}
    try:
        _, creada = services.confirmar_precio(usuario=request.user, reporte_id=reporte_id)
        contexto["confirmado"] = True
        contexto["mensaje"] = (
            "¡Gracias! Confirmaste que sigue igual." if creada else "Ya lo confirmaste hoy."
        )
    except ValidationError as exc:
        contexto["mensaje"] = " ".join(exc.messages)
    except services.LimiteDeConfirmacionesExcedidoError as exc:
        contexto["mensaje"] = str(exc)
    if not request.htmx:
        messages.info(request, contexto["mensaje"])
        return redirect(request.headers.get("Referer") or "comparacion:inicio")
    return render(request, "precios/partials/_sigue_igual.html", contexto)
