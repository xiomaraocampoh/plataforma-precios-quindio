from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.catalogo import selectors as catalogo

from . import selectors, services
from .forms import RegistroPrecioForm


def _id(valor) -> int | None:
    """Un id de la dirección: entero positivo o nada (la dirección la escribe cualquiera)."""
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return None
    return numero if numero > 0 else None


def _producto_pedido(request):
    """El producto del que se registra: `?producto=`, o el de la presentación indicada o enviada.

    Solo catálogo público: un producto retirado o inexistente equivale a «no hay producto» y la
    persona vuelve a elegir uno.
    """
    producto_id = _id(request.GET.get("producto"))
    if producto_id is not None:
        return catalogo.obtener_producto(producto_id)
    presentacion_id = _id(request.GET.get("presentacion") or request.POST.get("presentacion"))
    if presentacion_id is not None:
        presentacion = (
            catalogo.presentaciones_publicas()
            .select_related("producto")
            .filter(pk=presentacion_id)
            .first()
        )
        return presentacion.producto if presentacion else None
    return None


def _valores_iniciales(request, producto) -> dict:
    """Lo que ya se sabe: presentación y tienda de la dirección; si no, la única presentación y
    la última tienda de la persona. Menos campos por llenar = menos toques (M-01)."""
    iniciales = {}
    presentaciones = list(catalogo.presentaciones_publicas().filter(producto=producto)[:2])
    pedida = _id(request.GET.get("presentacion"))
    if pedida and catalogo.presentaciones_publicas().filter(producto=producto, pk=pedida).exists():
        iniciales["presentacion"] = pedida
    elif len(presentaciones) == 1:
        iniciales["presentacion"] = presentaciones[0].pk
    tienda = _id(request.GET.get("establecimiento")) or selectors.ultimo_establecimiento_id(
        request.user
    )
    if tienda:
        iniciales["establecimiento"] = tienda
    return iniciales


def _elegir_producto(request):
    """Paso 1: buscar un producto o tocar uno de los más reportados (sin listas largas)."""
    texto = (request.GET.get("q") or "").strip()
    contexto = {
        "q": texto,
        "establecimiento_id": _id(request.GET.get("establecimiento")),
        "resultados": list(catalogo.buscar_productos(texto)) if texto else None,
        "frecuentes": [] if texto else selectors.productos_para_registrar(),
    }
    if request.htmx and "q" in request.GET:
        return render(request, "precios/partials/_resultados_producto.html", contexto)
    plantilla = (
        "precios/partials/_elegir_producto.html" if request.htmx else "precios/registrar.html"
    )
    return render(request, plantilla, {**contexto, "paso": "producto"})


@login_required
@require_http_methods(["GET", "POST"])
def registrar(request):
    producto = _producto_pedido(request)
    if request.method == "GET" and producto is None:
        return _elegir_producto(request)
    if request.method == "POST":
        form = RegistroPrecioForm(request.POST, producto=producto)
        if form.is_valid():
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
                contexto = {
                    "reporte": reporte,
                    "producto": d["presentacion"].producto,
                    "establecimiento": d["establecimiento"],
                }
                return render(request, "precios/partials/_confirmacion.html", contexto)
    else:
        form = RegistroPrecioForm(initial=_valores_iniciales(request, producto), producto=producto)
    contexto = {"form": form, "producto": form.producto or producto, "paso": "formulario"}
    plantilla = "precios/partials/_formulario.html" if request.htmx else "precios/registrar.html"
    return render(request, plantilla, contexto)


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
