"""Vistas HTMX de moderación: denunciar (RF-20) y bandeja con decisiones (RF-21, RF-22)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from . import selectors, services
from .forms import DecisionForm, DenunciaForm
from .permisos import solo_moderadores

_DECISIONES = {
    "reporte": lambda m, i, a, mot: services.decidir_reporte(
        moderador=m, reporte_id=i, aprobar=a, motivo=mot
    ),
    "denuncia": lambda m, i, a, mot: services.resolver_denuncia(
        moderador=m, denuncia_id=i, aceptar=a, motivo=mot
    ),
    "solicitud": lambda m, i, a, mot: services.decidir_solicitud(
        moderador=m, solicitud_id=i, aprobar=a, motivo=mot
    ),
    "establecimiento": lambda m, i, a, mot: services.decidir_establecimiento(
        moderador=m, establecimiento_id=i, aprobar=a, motivo=mot
    ),
    "usuario": lambda m, i, _a, mot: services.suspender_cuenta(
        moderador=m, usuario_id=i, motivo=mot
    ),
}


@login_required
@require_http_methods(["GET", "POST"])
def denunciar(request, reporte_id: int):
    form = DenunciaForm(request.POST or None, reporte_id=reporte_id)
    contexto = {"form": form, "reporte_id": reporte_id, "listo": False, "mensaje": ""}
    if request.method == "POST" and form.is_valid():
        try:
            services.denunciar(
                denunciante=request.user,
                reporte_id=reporte_id,
                motivo=form.cleaned_data["motivo"],
                detalle=form.cleaned_data["detalle"],
            )
            contexto.update(listo=True, mensaje="Gracias. Moderación revisará este precio.")
        except services.DenunciaDuplicadaError as exc:
            contexto.update(listo=True, mensaje=str(exc))
        except ValidationError as exc:
            contexto["mensaje"] = " ".join(exc.messages)
    if not request.htmx and request.method == "POST":
        messages.info(request, contexto["mensaje"] or "Revisa el motivo de la denuncia.")
        return redirect(request.headers.get("Referer") or "comparacion:inicio")
    plantilla = (
        "moderacion/partials/_denunciar.html" if request.htmx else "moderacion/denunciar.html"
    )
    return render(request, plantilla, contexto)


@solo_moderadores
@require_GET
def bandeja(request):
    return render(request, "moderacion/bandeja.html", selectors.bandeja())


@solo_moderadores
@require_POST
def decidir(request):
    form = DecisionForm(request.POST)
    mensaje, ok = "La decisión no es válida.", False
    if form.is_valid():
        d = form.cleaned_data
        try:
            _DECISIONES[d["tipo"]](
                request.user, d["objeto_id"], d["decision"] == "aprobar", d["motivo"]
            )
            mensaje, ok = "Decisión registrada.", True
        except (ValidationError, ValueError, ObjectDoesNotExist) as exc:
            mensaje = " ".join(getattr(exc, "messages", [str(exc)]))
    if request.htmx:
        return render(request, "moderacion/partials/_decision.html", {"mensaje": mensaje, "ok": ok})
    (messages.success if ok else messages.error)(request, mensaje)
    return redirect("moderacion:bandeja")
