"""Directorio de establecimientos con filtros y sugerencias (RF-08, RF-09, RF-10)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from . import selectors, services
from .forms import SugerenciaForm


@require_GET
def directorio(request):
    filtros = {k: request.GET.get(k, "").strip() for k in ("municipio", "barrio", "tipo")}
    contexto = {
        "establecimientos": selectors.directorio(**filtros),
        "filtros": filtros,
        **selectors.opciones_directorio(filtros["municipio"]),
    }
    plantilla = (
        "establecimientos/partials/_lista.html"
        if request.htmx
        else "establecimientos/directorio.html"
    )
    return render(request, plantilla, contexto)


@login_required
@require_http_methods(["GET", "POST"])
def sugerir(request):
    form = SugerenciaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        services.sugerir_establecimiento(autor=request.user, **form.cleaned_data)
        messages.success(
            request,
            "Gracias. El establecimiento quedó pendiente; aparecerá cuando lo apruebe moderación.",
        )
        return redirect("establecimientos:directorio")
    return render(request, "establecimientos/sugerir.html", {"form": form})
