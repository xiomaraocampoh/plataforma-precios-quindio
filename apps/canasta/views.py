"""Canasta de compra: la persona arma su lista y ve en qué tienda le sale mejor comprarla toda."""

from django.http import Http404
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from . import selectors, services
from .domain.canasta import CanastaInvalidaError


def _panel(request, error: str = ""):
    criterio = request.GET.get("criterio") or request.POST.get("criterio", "")
    contexto = {
        "panel": selectors.panel(services.leer(request.session), criterio),
        "criterios": selectors.CRITERIOS,
        "error": error,
    }
    return render(request, "canasta/partials/_panel.html", contexto)


@require_GET
def inicio(request):
    contexto = {
        "panel": selectors.panel(services.leer(request.session)),
        "criterios": selectors.CRITERIOS,
        "error": "",
    }
    return render(request, "canasta/canasta.html", contexto)


@require_GET
def buscar(request):
    texto = request.GET.get("q", "").strip()
    productos = list(selectors.productos_buscables(texto)) if len(texto) >= 2 else []
    en_lista = {i["producto_id"] for i in services.leer(request.session)}
    return render(
        request,
        "canasta/partials/_buscar.html",
        {"productos": productos, "texto": texto, "en_lista": en_lista, "corto": len(texto) < 2},
    )


@require_GET
def resultado(request):
    return _panel(request)


@require_POST
def agregar(request):
    producto_id = request.POST.get("producto_id", "")
    producto = selectors.producto_de(int(producto_id)) if producto_id.isdigit() else None
    if producto is None:
        raise Http404("Producto no encontrado.")
    try:
        services.agregar(request.session, producto.pk, selectors.unidades_de(producto)[0])
    except CanastaInvalidaError as exc:
        return _panel(request, str(exc))
    return _panel(request)


@require_POST
def cambiar(request, producto_id: int):
    producto = selectors.producto_de(producto_id)
    if producto is None:
        raise Http404("Producto no encontrado.")
    try:
        services.cambiar(
            request.session,
            producto_id,
            request.POST.get("cantidad", ""),
            request.POST.get("unidad", ""),
            selectors.unidades_de(producto),
        )
    except CanastaInvalidaError as exc:
        return _panel(request, str(exc))
    return _panel(request)


@require_POST
def quitar(request, producto_id: int):
    services.quitar(request.session, producto_id)
    return _panel(request)


@require_POST
def vaciar(request):
    services.vaciar(request.session)
    return _panel(request)
