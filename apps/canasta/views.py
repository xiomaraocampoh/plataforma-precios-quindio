"""Asistente de compras: una conversación para saber dónde comprar toda la lista más barato."""

from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from . import selectors, services
from .domain.guia import tema_por_id

EXTENSIONES_TEXTO = (".txt", ".csv", ".md")
MAX_IMAGEN = 5_000_001  # un byte más del tope: así se detecta una imagen demasiado grande
EJEMPLO = "2 kg arroz\n1 L leche\n12 huevos\n1 kg azúcar\n500 g café"


def _contexto(request) -> dict:
    estado = services.leer(request.session)
    mensajes = estado["mensajes"]
    ultima = max((n for n, m in enumerate(mensajes) if m["tarjeta"]), default=None)
    resultado = None
    if ultima is not None and estado["pedido"]:
        resultado = selectors.resultado(estado["pedido"], estado["criterio"])
    return {
        "mensajes": mensajes,
        "indice_tarjeta": ultima,
        "resultado": resultado,
        "ejemplo": EJEMPLO,
        "atajos": [
            {"texto": t.titulo, "tema": t.id, "etiqueta": t.corto, "icono": t.icono}
            for t in (tema_por_id(i) for i in services.PRINCIPALES)
        ],
    }


def _adjunto(archivo):
    if archivo is None:
        return None
    if (archivo.content_type or "").startswith("image/"):
        return services.Adjunto(archivo.name, es_imagen=True, imagen=archivo.read(MAX_IMAGEN))
    if not archivo.name.lower().endswith(EXTENSIONES_TEXTO) or archivo.size > 200_000:
        return services.Adjunto(archivo.name, es_imagen=False, texto="")
    texto = archivo.read(services.MAX_ADJUNTO * 4).decode("utf-8", errors="replace")
    return services.Adjunto(archivo.name, texto=texto)


@require_GET
def inicio(request):
    return render(request, "canasta/asistente.html", _contexto(request))


@require_GET
def cuerpo(request):
    """El cuerpo del chat que se abre en el botón flotante (se pide al abrirlo, no antes)."""
    return render(request, "canasta/partials/_panel.html", _contexto(request))


@require_POST
def enviar(request):
    texto = request.POST.get("mensaje", "")
    if request.POST.get("reiniciar"):
        services.reiniciar(request.session)
    elif request.POST.get("tema") and services.responder_tema(
        request.session, texto, request.POST["tema"]
    ):
        pass  # un botón de la guía: ya respondió, sin IA
    else:
        services.responder(
            request.session,
            texto[:4000],
            _adjunto(request.FILES.get("archivo")),
            usuario=request.user,
            ip=request.META.get("REMOTE_ADDR", ""),
        )
    plantilla = "canasta/partials/_hilo.html" if request.htmx else "canasta/asistente.html"
    return render(request, plantilla, _contexto(request))
