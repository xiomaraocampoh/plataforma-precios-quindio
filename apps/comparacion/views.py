"""Vistas HTMX del consumidor. Renderizan página completa o solo el fragmento (partial)."""

from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from apps.catalogo import selectors as catalogo
from apps.catalogo.models import Producto
from apps.integraciones.selectors import referencia_sipsa

from .domain.filtros import FiltroUbicacion
from .domain.ranking import CRITERIO_DECLARADO
from .selectors import (
    buscar_productos,
    comparar_con_resumen,
    comparar_filas,
    ejemplo_comparacion,
    estado_del_usuario,
    productos_destacados,
    resumen_plataforma,
    ubicaciones_de,
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
    """hx-get con hx-trigger='keyup changed delay:300ms' → solo el fragmento de sugerencias."""
    productos = buscar_productos(request.GET.get("q", ""))
    return render(request, "comparacion/partials/_sugerencias.html", {"productos": productos})


@require_GET
def comparar(request, producto_id: int):
    producto = get_object_or_404(Producto.objects.select_related("categoria"), pk=producto_id)
    filtro = FiltroUbicacion(
        municipio=request.GET.get("municipio", ""), barrio=request.GET.get("barrio", "")
    )
    filas, resumen = comparar_con_resumen(producto_id, filtro)
    ids = [f.reporte_id for f in filas]
    contexto = {
        "producto": producto,
        "filas": filas,
        "resumen": resumen,
        "criterio": CRITERIO_DECLARADO,
        "filtro": filtro,
        **ubicaciones_de(comparar_filas(producto_id)),
        **estado_del_usuario(request.user, ids),
        "referencia": referencia_sipsa(producto_id),
    }
    plantilla = (
        "comparacion/partials/_resultados.html" if request.htmx else "comparacion/comparar.html"
    )
    return render(request, plantilla, contexto)


@require_GET
def productos(request):
    """Listado de productos con filtros de marca y categoría (RF-04, RF-19 prioridad C)."""
    texto = request.GET.get("q", "").strip()
    marca = request.GET.get("marca", "").strip()
    categoria = request.GET.get("categoria", "")
    categoria_id = int(categoria) if categoria.isdigit() else None
    lista = catalogo.listar_productos(texto=texto, marca=marca, categoria_id=categoria_id)
    pagina = Paginator(lista, 24).get_page(request.GET.get("pagina"))
    contexto = {
        "pagina": pagina,
        "q": texto,
        "marca": marca,
        "categoria_id": categoria_id,
        "consulta": urlencode({k: v for k, v in request.GET.items() if k != "pagina" and v}),
        **catalogo.opciones_de_filtro(),
    }
    plantilla = (
        "comparacion/partials/_productos.html" if request.htmx else "comparacion/productos.html"
    )
    return render(request, plantilla, contexto)
