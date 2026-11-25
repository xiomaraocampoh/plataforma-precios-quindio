"""Vista previa de los correos en el navegador (solo staff), con datos de ejemplo ficticios."""

from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .domain.catalogo import Tipo, categoria_de
from .services import renderizar

_ENLACE = "https://ahorrapues.example/enlace-de-ejemplo/"
EJEMPLOS: dict[str, dict] = {
    Tipo.VERIFICAR_CORREO: {"nombre": "lucia", "enlace": _ENLACE},
    Tipo.RECUPERAR_CONTRASENA: {"nombre": "lucia", "enlace": _ENLACE},
    Tipo.CONTRASENA_CAMBIADA: {
        "nombre": "lucia",
        "cuando": "16 de noviembre de 2026, 10:30",
        "enlace": _ENLACE,
    },
    Tipo.NUEVO_DISPOSITIVO: {
        "nombre": "lucia",
        "navegador": "Chrome en Android",
        "cuando": "16 de noviembre de 2026, 10:30",
    },
    Tipo.CODIGO_VERIFICACION: {
        "nombre": "lucia",
        "codigo": "000000",
        "proposito": "ingresar a tu cuenta",
    },
    Tipo.CUENTA_SUSPENDIDA: {"nombre": "lucia"},
    Tipo.CUENTA_SUPRIMIDA: {"nombre": "lucia"},
    Tipo.BIENVENIDA: {"nombre": "lucia"},
    Tipo.DENUNCIA_RESUELTA: {
        "nombre": "lucia",
        "aprobado": True,
        "producto": "Arroz blanco 500 g",
        "establecimiento": "Tienda Doña Rosa",
        "producto_id": 1,
    },
    Tipo.REPORTE_MODERADO: {
        "nombre": "lucia",
        "aprobado": False,
        "presentacion": "Leche entera 1 L",
        "precio": "9.800",
        "establecimiento": "Súper Quindío",
    },
    Tipo.SOLICITUD_RESUELTA: {"nombre": "lucia", "aprobado": True, "producto": "Lentejas Diana"},
    Tipo.ESTABLECIMIENTO_RESUELTO: {
        "nombre": "lucia",
        "aprobado": False,
        "establecimiento": "Tienda La Esquina",
    },
    Tipo.PERFIL_VERIFICADO: {
        "nombre": "rosa",
        "aprobado": True,
        "establecimiento": "Tienda Doña Rosa",
        "motivo": "",
        "enlace_portal": "https://ahorrapues.example/comercios/",
    },
    Tipo.CORRECCION_RESUELTA: {
        "nombre": "rosa",
        "aprobado": True,
        "establecimiento": "Tienda Doña Rosa",
        "respuesta": "Actualizamos la dirección del local.",
        "enlace_portal": "https://ahorrapues.example/comercios/",
    },
}


def _solo_staff(request) -> None:
    if not (request.user.is_authenticated and request.user.is_staff):
        raise PermissionDenied("La vista previa de correos es solo para el personal.")


@require_GET
def indice(request):
    _solo_staff(request)
    tipos = [(t.value, categoria_de(t).value) for t in Tipo]
    return render(request, "notificaciones/vista_previa.html", {"tipos": tipos})


@require_GET
def vista_previa(request, tipo: str):
    _solo_staff(request)
    if tipo not in {t.value for t in Tipo}:
        raise Http404("Ese correo no existe.")
    datos = dict(EJEMPLOS[Tipo(tipo)])
    if "aprobado" in datos and request.GET.get("aprobado") in ("0", "1"):
        datos["aprobado"] = request.GET["aprobado"] == "1"
    asunto, texto, html = renderizar(tipo, datos)
    if request.GET.get("formato") == "texto":
        return HttpResponse(
            f"Asunto: {asunto}\n\n{texto}", content_type="text/plain; charset=utf-8"
        )
    return HttpResponse(html)
