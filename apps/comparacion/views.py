"""Vistas HTMX del consumidor. Renderizan página completa o solo el fragmento (partial)."""

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from apps.catalogo.models import Producto

from .domain.ranking import CRITERIO_DECLARADO
from .selectors import (
    MIN_CARACTERES_BUSQUEDA,
    buscar_productos,
    comparar_con_resumen,
    ejemplo_comparacion,
    productos_destacados,
    resumen_plataforma,
)


@require_GET
def inicio(request):
    destacados = productos_destacados()
    contexto = {
        "resumen": resumen_plataforma(),
        "destacados": destacados,
        "ejemplo_producto": destacados[0] if destacados else None,
        "ejemplo": ejemplo_comparacion(destacados[0].pk) if destacados else [],
    }
    return render(request, "comparacion/buscar.html", contexto)


@require_GET
def sugerencias(request):
    """Fragmento de sugerencias (hx-trigger: input changed delay:300ms, search)."""
    texto = request.GET.get("q", "").strip()
    if not texto:
        return HttpResponse("")  # Esc o campo vacío: la lista queda vacía y se oculta
    contexto = {
        "productos": buscar_productos(texto),
        "texto": texto,
        "muy_corto": len(texto) < MIN_CARACTERES_BUSQUEDA,
    }
    return render(request, "comparacion/partials/_sugerencias.html", contexto)


@require_GET
def comparar(request, producto_id: int):
    producto = get_object_or_404(Producto.objects.select_related("categoria"), pk=producto_id)
    resultados, resumen = comparar_con_resumen(producto_id)
    contexto = {
        "producto": producto,
        "resultados": resultados,
        "resumen": resumen,
        "criterio": CRITERIO_DECLARADO,
    }
    plantilla = (
        "comparacion/partials/_resultados.html" if request.htmx else "comparacion/comparar.html"
    )
    return render(request, plantilla, contexto)
