"""Vistas HTMX del consumidor. Renderizan página completa o solo el fragmento (partial)."""

from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from rest_framework.throttling import ScopedRateThrottle

from apps.catalogo import selectors as catalogo
from apps.catalogo.domain.codigo_barras import es_gtin_valido, normalizar_codigo
from apps.catalogo.domain.normalizacion import formatear_cantidad
from apps.establecimientos import selectors as establecimientos
from apps.integraciones import services as integraciones
from apps.integraciones.domain.reconocimiento import (
    ImagenInvalidaError,
    consulta_de_busqueda,
)
from apps.integraciones.selectors import referencia_sipsa

from .domain.filtros import FiltroPrecio, FiltroUbicacion, interpretar_monto
from .domain.ranking import CRITERIO_DECLARADO
from .selectors import (
    MIN_CARACTERES_BUSQUEDA,
    buscar_productos,
    categorias_frecuentes,
    comparar_con_resumen,
    comparar_filas,
    ejemplo_comparacion,
    estado_del_usuario,
    filas_de_establecimiento,
    productos_destacados,
    propuesta_de_escaneo,
    resumen_plataforma,
    tarjetas_de_productos,
    ubicaciones_de,
)


@require_GET
def inicio(request):
    destacados = productos_destacados()
    contexto = {
        "resumen": resumen_plataforma(),
        "destacados": destacados,
        "categorias_rapidas": categorias_frecuentes(),
        "ejemplo_producto": destacados[0] if destacados else None,
        "ejemplo": ejemplo_comparacion(destacados[0].pk) if destacados else [],
        "foto_activa": integraciones.reconocimiento_activo(),
        "vivo_activo": integraciones.escaneo_vivo_activo(),
        "control_envio": integraciones.control_de_envio(),
    }
    return render(request, "comparacion/buscar.html", contexto)


@require_GET
def escanear(request):
    """RF-04: un código leído con la cámara (o escrito) lleva a la comparación del producto.

    La imagen nunca llega al servidor: el navegador la decodifica y solo envía los dígitos.
    """
    codigo = normalizar_codigo(request.GET.get("codigo", ""))
    valido = es_gtin_valido(codigo)
    if valido:
        encontrados = list(catalogo.productos_por_codigo(codigo)[:2])
        if len(encontrados) == 1:
            return redirect("comparacion:comparar", producto_id=encontrados[0].pk)
        if encontrados:  # el mismo código en varios productos: que la persona elija
            return redirect(f"{reverse('comparacion:productos')}?{urlencode({'q': codigo})}")
    return render(request, "comparacion/escanear.html", {"codigo": codigo, "valido": valido})


def _fragmento_foto(request, estado: int, **contexto):
    return render(request, "comparacion/partials/_foto_resultado.html", contexto, status=estado)


@require_POST
def buscar_por_foto(request):
    """Fragmento: qué producto parece ser el de la foto. La IA solo extrae texto; el orden y los
    precios siguen saliendo del catálogo. La persona confirma antes de ir a la comparación."""
    archivo = request.FILES.get("foto")
    if archivo is None:
        return _fragmento_foto(request, 400, error="Elige o toma una foto del producto.")
    try:
        pista = integraciones.reconocer_producto(
            usuario=request.user, imagen=archivo.read(), ip=request.META.get("REMOTE_ADDR", "")
        )
    except ImagenInvalidaError as exc:
        return _fragmento_foto(request, 400, error=str(exc))
    except integraciones.LimiteDeReconocimientosExcedidoError as exc:
        return _fragmento_foto(request, 429, error=str(exc))
    except integraciones.ReconocimientoNoDisponibleError:
        return _fragmento_foto(
            request,
            503,
            error="La búsqueda por foto no está disponible ahora. "
            "Busca con el nombre o con el código de barras.",
        )
    if pista is None:
        return _fragmento_foto(request, 200, no_reconocido=True)
    candidatos = catalogo.buscar_por_pista(
        nombre=pista.nombre,
        marca=pista.marca,
        cantidad=pista.cantidad,
        unidad=pista.unidad,
        codigo=pista.codigo_barras,
    )
    return _fragmento_foto(
        request, 200, pista=pista, candidatos=candidatos, buscamos=consulta_de_busqueda(pista)
    )


class _RitmoDeEscaneo:
    throttle_scope = "escaneo"  # M-13: mismo mecanismo que la API, aunque responda HTML


def _fragmento_escaneo(request, estado: int, **contexto):
    return render(request, "comparacion/partials/_escaneo_resultado.html", contexto, status=estado)


@require_POST
def escanear_fotograma(request):
    """Escáner en vivo (ADR-0026): qué hay en un fotograma. 204 si no hay nada que mostrar, así el
    navegador sigue escaneando sin abrir la hoja. La imagen no se guarda en ningún lado."""
    if not integraciones.escaneo_vivo_activo():
        raise Http404
    if not ScopedRateThrottle().allow_request(request, _RitmoDeEscaneo):
        return _fragmento_escaneo(request, 429, error="Vas muy rápido. Espera un momento.")
    archivo = request.FILES.get("fotograma")
    if archivo is None:
        return _fragmento_escaneo(request, 400, error="No llegó la imagen de la cámara.")
    try:
        resultado = integraciones.escanear_fotograma(
            usuario=request.user, imagen=archivo.read(), ip=request.META.get("REMOTE_ADDR", "")
        )
    except ImagenInvalidaError as exc:
        return _fragmento_escaneo(request, 400, error=str(exc))
    except integraciones.LimiteDeReconocimientosExcedidoError as exc:
        return _fragmento_escaneo(request, 429, error=str(exc))
    except integraciones.ReconocimientoNoDisponibleError:
        return _fragmento_escaneo(
            request, 503, error="El reconocimiento no respondió. Sigue con el código de barras."
        )
    propuesta = propuesta_de_escaneo(resultado, request.user)
    if propuesta is None:
        return HttpResponse(status=204)
    return _fragmento_escaneo(request, 200, p=propuesta)


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


def _leer_filtro_precio(parametros) -> tuple[FiltroPrecio, str]:
    """Lee el rango de precio de la URL. Si es inválido no filtra y devuelve un aviso."""
    try:
        minimo = interpretar_monto(parametros.get("precio_min", ""))
        maximo = interpretar_monto(parametros.get("precio_max", ""))
        return FiltroPrecio(minimo=minimo, maximo=maximo), ""
    except ValueError as error:
        return FiltroPrecio(), f"No se aplicó el filtro de precio. {error}"


@require_GET
def comparar(request, producto_id: int):
    producto = get_object_or_404(catalogo.productos_publicos(), pk=producto_id)
    filtro = FiltroUbicacion(
        municipio=request.GET.get("municipio", ""), barrio=request.GET.get("barrio", "")
    )
    filtro_precio, error_precio = _leer_filtro_precio(request.GET)
    filas, resumen = comparar_con_resumen(producto_id, filtro, filtro_precio)
    todas = comparar_filas(producto_id)
    ids = [f.reporte_id for f in filas]
    presentaciones = [
        {"texto": f"{formatear_cantidad(p.cantidad)} {p.unidad}", "codigo": p.codigo_barras}
        for p in catalogo.presentaciones_publicas()
        .filter(producto=producto)
        .order_by("unidad", "cantidad")
    ]
    contexto = {
        "producto": producto,
        "filas": filas,
        "resumen": resumen,
        "criterio": CRITERIO_DECLARADO,
        "filtro": filtro,
        "filtro_precio": filtro_precio,
        "error_precio": error_precio,
        "precio_min": request.GET.get("precio_min", ""),
        "precio_max": request.GET.get("precio_max", ""),
        "total": len(todas),
        "presentaciones": presentaciones,
        "con_codigo": [p for p in presentaciones if p["codigo"]],
        **ubicaciones_de(todas),
        **estado_del_usuario(request.user, ids),
        "referencia": referencia_sipsa(producto_id),
    }
    plantilla = (
        "comparacion/partials/_resultados.html" if request.htmx else "comparacion/comparar.html"
    )
    return render(request, plantilla, contexto)


@require_GET
def establecimiento(request, establecimiento_id: int):
    """Precios vigentes registrados en un comercio, en orden alfabético (no es un ranking)."""
    local = establecimientos.establecimiento_publico(establecimiento_id)
    if local is None:
        raise Http404("Establecimiento no encontrado.")
    filas = filas_de_establecimiento(local.pk)
    productos_de = {  # con su foto en el mismo query, sin traer los bytes
        p.pk: p
        for p in catalogo.con_fotos(catalogo.productos_publicos()).filter(
            pk__in={f.producto_id for f in filas}
        )
    }
    tarjetas = [(productos_de[f.producto_id], f) for f in filas if f.producto_id in productos_de]
    contexto = {
        "local": local,
        "tarjetas": tarjetas,
        **estado_del_usuario(request.user, [f.reporte_id for _, f in tarjetas]),
    }
    return render(request, "comparacion/establecimiento.html", contexto)


@require_GET
def productos(request):
    """Listado de productos con filtros de marca y categoría (RF-04, RF-19 prioridad C)."""
    texto = request.GET.get("q", "").strip()
    marca = request.GET.get("marca", "").strip()
    categoria = request.GET.get("categoria", "")
    categoria_id = int(categoria) if categoria.isdigit() else None
    lista = catalogo.listar_productos(texto=texto, marca=marca, categoria_id=categoria_id)
    pagina = Paginator(lista, 24).get_page(request.GET.get("pagina"))
    tarjetas = tarjetas_de_productos(pagina.object_list)  # un lote: sin N+1
    ids = [fila.reporte_id for _, fila in tarjetas if fila is not None]
    contexto = {
        "pagina": pagina,
        "tarjetas": tarjetas,
        **estado_del_usuario(request.user, ids),
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
