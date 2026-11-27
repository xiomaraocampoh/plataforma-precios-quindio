"""Portal HTMX de comercios (RF-C01 a RF-C07) y bandeja de verificación para moderación (RF-C02).

La misma vista sirve la página completa o el fragmento de la sección (`request.htmx`). Las vistas
no escriben con el ORM: llaman a `services` y leen con `selectors`.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from . import selectors, services
from .forms import CorreccionForm, DecisionForm, PerfilForm, PrecioOficialForm, PromocionForm
from .models import DocumentoComercio
from .permisos import es_moderador, solo_moderadores

ERRORES_DE_SERVICIO = (ValidationError, PermissionDenied, ObjectDoesNotExist, ValueError)


def _mensaje_de(exc: Exception) -> str:
    return " ".join(getattr(exc, "messages", None) or [str(exc)])


def _contexto(request, **formularios) -> dict:
    perfil = selectors.perfil_de(request.user)
    contexto = {"perfil": perfil, "rechazo": None, "mensaje": "", "ok": False}
    if perfil is None:
        contexto["rechazo"] = selectors.ultimo_rechazo(request.user)
        contexto["form_perfil"] = formularios.get("form_perfil") or PerfilForm()
        return contexto
    if perfil.verificado:
        reportes = selectors.reportes_de_su_tienda(perfil)
        contexto.update(
            precios=selectors.precios_del_portal(perfil),
            promociones=selectors.promociones_del_portal(perfil),
            correcciones=selectors.correcciones_del_perfil(perfil),
            form_precio=formularios.get("form_precio") or PrecioOficialForm(),
            form_promocion=formularios.get("form_promocion") or PromocionForm(perfil=perfil),
            form_correccion=formularios.get("form_correccion") or CorreccionForm(reportes=reportes),
        )
    return contexto


def _responder(request, seccion: str, mensaje: str, ok: bool, **formularios):
    """HTMX: solo la sección, con el mensaje en una región aria-live. Sin HTMX: página completa."""
    if request.htmx:
        contexto = _contexto(request, **formularios) | {"mensaje": mensaje, "ok": ok}
        return render(request, f"comercios/partials/_{seccion}.html", contexto)
    if mensaje:
        (messages.success if ok else messages.error)(request, mensaje)
    if formularios and not ok:
        return render(request, "comercios/portal.html", _contexto(request, **formularios))
    return redirect("comercios:inicio")


@login_required
@require_GET
def inicio(request):
    return render(request, "comercios/portal.html", _contexto(request))


@login_required
@require_POST
def crear_perfil(request):
    form = PerfilForm(request.POST, request.FILES)
    if not form.is_valid():
        return _responder(
            request, "perfil", "Revisa los datos del perfil.", False, form_perfil=form
        )
    d = form.cleaned_data
    try:
        services.crear_perfil(
            usuario=request.user,
            establecimiento_id=d["establecimiento"].pk,
            nombre_contacto=d["nombre_contacto"],
            telefono=d["telefono"],
            camara_comercio=d["camara_comercio"],
            rut=d["rut"],
        )
    except ERRORES_DE_SERVICIO as exc:
        return _responder(request, "perfil", _mensaje_de(exc), False, form_perfil=form)
    return _responder(request, "perfil", "Recibimos tu perfil. Moderación lo revisará.", True)


@login_required
@require_POST
def publicar_precio(request):
    form = PrecioOficialForm(request.POST)
    if not form.is_valid():
        return _responder(request, "precios", "Revisa el precio.", False, form_precio=form)
    try:
        services.publicar_precio_oficial(
            usuario=request.user,
            presentacion_id=form.cleaned_data["presentacion"].pk,
            precio=form.cleaned_data["precio"],
        )
    except ERRORES_DE_SERVICIO as exc:
        return _responder(request, "precios", _mensaje_de(exc), False, form_precio=form)
    return _responder(request, "precios", "Precio oficial publicado por 30 días.", True)


@login_required
@require_POST
def retirar_precio(request, precio_id: int):
    try:
        services.retirar_precio_oficial(usuario=request.user, precio_id=precio_id)
    except ERRORES_DE_SERVICIO as exc:
        return _responder(request, "precios", _mensaje_de(exc), False)
    return _responder(request, "precios", "Retiramos ese precio oficial.", True)


@login_required
@require_POST
def confirmar_vigencia(request):
    try:
        n = services.confirmar_vigencia(usuario=request.user)
    except ERRORES_DE_SERVICIO as exc:
        return _responder(request, "precios", _mensaje_de(exc), False)
    texto = "precio sigue" if n == 1 else "precios siguen"
    return _responder(request, "precios", f"Listo: {n} {texto} vigentes 30 días más.", True)


@login_required
@require_POST
def crear_promocion(request):
    perfil = selectors.perfil_de(request.user)
    form = PromocionForm(request.POST, perfil=perfil)
    if not form.is_valid():
        return _responder(
            request, "promociones", "Revisa la promoción.", False, form_promocion=form
        )
    try:
        services.crear_promocion(usuario=request.user, **form.datos_para_servicio())
    except ERRORES_DE_SERVICIO as exc:
        return _responder(request, "promociones", _mensaje_de(exc), False, form_promocion=form)
    return _responder(request, "promociones", "Promoción publicada.", True)


@login_required
@require_POST
def finalizar_promocion(request, promocion_id: int):
    try:
        services.finalizar_promocion(usuario=request.user, promocion_id=promocion_id)
    except ERRORES_DE_SERVICIO as exc:
        return _responder(request, "promociones", _mensaje_de(exc), False)
    return _responder(request, "promociones", "Terminamos la promoción.", True)


@login_required
@require_POST
def solicitar_correccion(request):
    perfil = selectors.perfil_de(request.user)
    reportes = selectors.reportes_de_su_tienda(perfil) if perfil else []
    form = CorreccionForm(request.POST, reportes=reportes)
    if not form.is_valid():
        return _responder(
            request, "correcciones", "Revisa la solicitud.", False, form_correccion=form
        )
    try:
        services.solicitar_correccion(
            usuario=request.user,
            tipo=form.cleaned_data["tipo"],
            descripcion=form.cleaned_data["descripcion"],
            reporte_id=form.cleaned_data["reporte"],
        )
    except ERRORES_DE_SERVICIO as exc:
        return _responder(request, "correcciones", _mensaje_de(exc), False, form_correccion=form)
    return _responder(request, "correcciones", "Enviamos tu solicitud a moderación.", True)


# ---------- Moderación (RF-C02, RF-C06) ----------


@solo_moderadores
@require_GET
def verificacion(request):
    return render(
        request,
        "comercios/verificacion.html",
        {
            "perfiles": selectors.perfiles_pendientes(),
            "correcciones": selectors.correcciones_pendientes(),
        },
    )


def _decidir(request, accion) -> tuple[str, bool]:
    form = DecisionForm(request.POST)
    if not form.is_valid():
        return "La decisión no es válida.", False
    try:
        accion(form.cleaned_data["decision"] == "aprobar", form.cleaned_data["motivo"])
    except ERRORES_DE_SERVICIO as exc:
        return _mensaje_de(exc), False
    return "Decisión registrada.", True


def _respuesta_decision(request, mensaje: str, ok: bool):
    if request.htmx:
        return render(request, "comercios/partials/_decision.html", {"mensaje": mensaje, "ok": ok})
    (messages.success if ok else messages.error)(request, mensaje)
    return redirect("comercios:verificacion")


@solo_moderadores
@require_http_methods(["POST"])
def decidir_perfil(request, perfil_id: int):
    mensaje, ok = _decidir(
        request,
        lambda aprobar, motivo: services.verificar_perfil(
            moderador=request.user, perfil_id=perfil_id, aprobar=aprobar, motivo=motivo
        ),
    )
    return _respuesta_decision(request, mensaje, ok)


@solo_moderadores
@require_http_methods(["POST"])
def decidir_correccion(request, solicitud_id: int):
    mensaje, ok = _decidir(
        request,
        lambda aceptar, respuesta: services.resolver_correccion(
            moderador=request.user, solicitud_id=solicitud_id, aceptar=aceptar, respuesta=respuesta
        ),
    )
    return _respuesta_decision(request, mensaje, ok)


NOMBRE_DESCARGA = {
    DocumentoComercio.Tipo.CAMARA_COMERCIO: "camara-comercio",
    DocumentoComercio.Tipo.RUT: "rut",
}


@login_required
@require_GET
def documento_perfil(request, perfil_id: int, tipo: str):
    """ADR-0034: el PDF de evidencia, solo para moderación. Para los demás no existe (404)."""
    if not es_moderador(request.user) or tipo not in NOMBRE_DESCARGA:
        raise Http404
    documento = selectors.documento_de_perfil(perfil_id, tipo)
    if documento is None:
        raise Http404
    if documento.contenido is None:
        contexto = {"documento": documento}
        return render(request, "comercios/documento_borrado.html", contexto, status=410)
    respuesta = HttpResponse(bytes(documento.contenido), content_type="application/pdf")
    nombre = f"{NOMBRE_DESCARGA[tipo]}-{perfil_id}.pdf"
    respuesta["Content-Disposition"] = f'inline; filename="{nombre}"'
    respuesta["X-Content-Type-Options"] = "nosniff"
    respuesta["Cache-Control"] = "private, no-store"
    return respuesta
