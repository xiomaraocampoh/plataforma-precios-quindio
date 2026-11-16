"""Ingreso en dos pasos (RF-27).

La sesión NO se autentica hasta superar el segundo paso: mientras tanto solo hay un «ingreso
pendiente» en la sesión. Así la API (SessionAuthentication) también exige el segundo factor.
"""

import time

from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.views import LoginView
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from apps.notificaciones.domain.privacidad import enmascarar_correo
from core.limites import ip_de, permitir

from .. import services
from ..domain.segundo_factor import Resultado
from ..forms import CodigoForm, IngresarForm, PrimerCodigoAppForm
from ..models import SegundoFactor, Usuario

sf = services.segundo_factor
PENDIENTE = "ap_ingreso_pendiente"
FLAG = "ap_segundo_factor"  # "verificado" | "no_requerido" (lo revisa el middleware)
VIGENCIA_PENDIENTE_S = 10 * 60
MENSAJES = {
    Resultado.INCORRECTO: "El código no es correcto. Revísalo e inténtalo de nuevo.",
    Resultado.VENCIDO: "El código venció. Pide uno nuevo.",
    Resultado.BLOQUEADO: "Demasiados intentos. Por seguridad espera 15 minutos.",
}


def completar_ingreso(request, usuario, *, verificado: bool, siguiente: str, confiar=False):
    """Abre la sesión, marca el segundo factor y avisa si es un dispositivo nuevo (RF-25)."""
    auth_login(request, usuario, backend="django.contrib.auth.backends.ModelBackend")
    request.session.pop(PENDIENTE, None)
    request.session[FLAG] = "verificado" if verificado else "no_requerido"
    services.correo.registrar_dispositivo(
        usuario, user_agent=request.META.get("HTTP_USER_AGENT", "")[:400], ip=ip_de(request)
    )
    respuesta = redirect(siguiente or "comparacion:inicio")
    if confiar:
        respuesta.set_cookie(
            sf.COOKIE_CONFIANZA,
            sf.firmar_confianza(usuario),
            max_age=sf.DIAS_CONFIANZA * 86400,
            httponly=True,
            secure=request.is_secure(),
            samesite="Lax",
        )
    return respuesta


class IngresarView(LoginView):
    authentication_form = IngresarForm  # mensajes claros y cuenta desactivada (UX de ingreso)
    template_name = "cuentas/ingresar.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        usuario = form.get_user()
        siguiente = self.get_success_url()
        cookie = self.request.COOKIES.get(sf.COOKIE_CONFIANZA)
        if not sf.pide_segundo_paso(usuario, cookie):
            de_confianza = sf.es_de_confianza(usuario, cookie)
            return completar_ingreso(
                self.request, usuario, verificado=de_confianza, siguiente=siguiente
            )
        self.request.session[PENDIENTE] = {"u": usuario.pk, "next": siguiente, "t": time.time()}
        if sf.necesita_inscribirse(usuario):
            return redirect("cuentas:ingresar_configurar")
        if sf.de(usuario).metodo != SegundoFactor.Metodo.APP:
            _enviar_codigo_limitado(self.request, usuario)
        return redirect("cuentas:ingresar_verificar")


def _pendiente(request) -> tuple[Usuario | None, str]:
    datos = request.session.get(PENDIENTE) or {}
    if not datos or time.time() - datos.get("t", 0) > VIGENCIA_PENDIENTE_S:
        request.session.pop(PENDIENTE, None)
        return None, ""
    usuario = Usuario.objects.filter(pk=datos["u"], is_active=True).first()
    return usuario, datos.get("next", "")


def _volver_a_ingresar(request):
    messages.info(request, "Tu ingreso venció. Escribe de nuevo tu usuario y contraseña.")
    return redirect("cuentas:ingresar")


def _enviar_codigo_limitado(request, usuario) -> bool:
    if not permitir("2fa-enviar", str(usuario.pk), maximo=3, ventana_s=10 * 60):
        return False
    return sf.enviar_codigo(usuario)


@require_http_methods(["GET", "POST"])
def verificar(request):
    """Segundo paso: código por correo, de la app o de respaldo."""
    usuario, siguiente = _pendiente(request)
    if usuario is None:
        return _volver_a_ingresar(request)
    form = CodigoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if not permitir("2fa-verificar", ip_de(request), maximo=20, ventana_s=5 * 60):
            form.add_error(None, MENSAJES[Resultado.BLOQUEADO])
        else:
            resultado = sf.verificar(usuario, form.cleaned_data["valor"])
            if resultado == Resultado.VALIDO:
                return completar_ingreso(
                    request,
                    usuario,
                    verificado=True,
                    siguiente=siguiente,
                    confiar=form.cleaned_data["confiar"],
                )
            form.add_error(None, MENSAJES[resultado])
    metodo = sf.de(usuario).metodo
    contexto = {
        "form": form,
        "usa_app": metodo == SegundoFactor.Metodo.APP,
        "puede_correo": sf.puede_usar_correo(usuario),
        "correo_enmascarado": enmascarar_correo(usuario.email) if usuario.email else "",
    }
    return render(request, "cuentas/verificar_ingreso.html", contexto)


@require_POST
def reenviar_codigo(request):
    usuario, _ = _pendiente(request)
    if usuario is None:
        return _volver_a_ingresar(request)
    _enviar_codigo_limitado(request, usuario)
    # El mismo mensaje pase lo que pase: no revela si el envío se limitó ni a qué correo va
    messages.info(request, "Si tu cuenta tiene un correo, te enviamos un código nuevo.")
    return redirect("cuentas:ingresar_verificar")


@require_http_methods(["GET", "POST"])
def configurar_al_ingresar(request):
    """Rol con 2FA obligatoria y sin método: configura la app antes de entrar."""
    usuario, siguiente = _pendiente(request)
    if usuario is None:
        return _volver_a_ingresar(request)
    secreto = request.session.setdefault("ap_totp_nuevo", sf.nuevo_secreto())
    form = PrimerCodigoAppForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            codigos = sf.activar_app(usuario, secreto=secreto, codigo=form.cleaned_data["codigo"])
        except ValidationError as exc:
            form.add_error("codigo", exc.messages[0])
        else:
            request.session.pop("ap_totp_nuevo", None)
            completar_ingreso(request, usuario, verificado=True, siguiente=siguiente)
            return render(
                request,
                "cuentas/codigos_respaldo.html",
                {"codigos": codigos, "siguiente": siguiente or "/"},
            )
    contexto = {
        "form": form,
        "qr": sf.qr_svg(sf.uri_totp(usuario, secreto)),
        "secreto": secreto,
        "al_ingresar": True,
    }
    return render(request, "cuentas/configurar_app.html", contexto)
