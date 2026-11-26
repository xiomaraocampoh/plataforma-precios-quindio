"""Vistas HTMX del catálogo: solicitud de productos con aviso de duplicados (RF-06, D-05)."""

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseNotModified
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from . import selectors, services
from .domain.codigo_barras import normalizar_codigo
from .domain.normalizacion import Unidad
from .forms import SolicitudForm


def _presentacion_pedida(parametros) -> dict:
    """Cantidad y unidad que trae el escáner (ADR-0026), solo si son válidas; si no, nada."""
    unidad, cantidad = parametros.get("unidad", ""), parametros.get("cantidad", "")
    try:
        numero = Decimal(cantidad)
    except InvalidOperation:
        return {}
    if unidad not in {u.value for u in Unidad} or not (numero.is_finite() and numero > 0):
        return {}
    return {"cantidad": numero, "unidad": unidad}


@login_required
@require_http_methods(["GET", "POST"])
def solicitar(request):
    inicial = {
        "codigo_barras": normalizar_codigo(request.GET.get("codigo_barras", ""))[:14],
        "nombre": request.GET.get("nombre", "")[:120],
        "marca": request.GET.get("marca", "")[:80],
        **_presentacion_pedida(request.GET),
    }
    form = SolicitudForm(request.POST or None, initial=inicial)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        services.solicitar_producto(
            solicitante=request.user,
            nombre=d["nombre"],
            marca=d["marca"],
            categoria_id=d["categoria"].pk,
            cantidad=d["cantidad"],
            unidad=d["unidad"],
            codigo_barras=d["codigo_barras"],
            detalle=d["detalle"],
        )
        messages.success(
            request, "Recibimos tu solicitud. Una persona moderadora la revisará pronto."
        )
        return redirect("comparacion:productos")
    similares = selectors.productos_similares(
        request.POST.get("nombre", ""), request.POST.get("marca", "")
    )
    return render(request, "catalogo/solicitar.html", {"form": form, "similares": similares})


@require_GET
def similares(request):
    """Fragmento HTMX: productos parecidos al nombre escrito (similitud ≥ 0,85, D-05)."""
    productos = selectors.productos_similares(
        request.GET.get("nombre", ""), request.GET.get("marca", "")
    )
    contexto = {"similares": productos, "nombre": request.GET.get("nombre", "").strip()}
    return render(request, "catalogo/partials/_similares.html", contexto)


@require_GET
def foto(request, producto_id: int):
    """Miniatura de un producto público. Pública y cacheable: no depende de quién la pida.

    Con la versión correcta en la dirección (`?v=`) el navegador la guarda un año; sin ella, solo
    unos minutos, para no dejar una foto vieja. ETag: si no cambió, responde 304 sin cuerpo.
    """
    datos = selectors.foto_de(producto_id)
    if datos is None:
        raise Http404("Este producto no tiene foto.")
    contenido, tipo, version = datos
    etag = f'"{version}"'
    if request.META.get("HTTP_IF_NONE_MATCH") == etag:
        respuesta = HttpResponseNotModified()
    else:
        respuesta = HttpResponse(contenido, content_type=tipo)
    respuesta["ETag"] = etag
    inmutable = request.GET.get("v") == version
    respuesta["Cache-Control"] = (
        "public, max-age=31536000, immutable" if inmutable else "public, max-age=300"
    )
    return respuesta
