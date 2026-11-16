"""Seguridad de la cuenta y correo (RF-02, RF-24, RF-25, RF-27).

Los mensajes nunca revelan si un correo existe. Las acciones sensibles piden la contraseña.
"""

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth import views as auth
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordResetForm
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST

from core.limites import ip_de, permitir

from .. import services
from ..forms import ActivarAppForm, ContrasenaActualForm, PreferenciasForm
from ..models import DispositivoConocido, SegundoFactor
from .ingreso import FLAG

sf = services.segundo_factor
correo = services.correo
EXPLICACION_ENLACE = {
    "vencido": "El enlace venció. Pide uno nuevo.",
    "usado": "El enlace ya se usó o ya no es válido.",
    "invalido": "El enlace no es válido. Revisa que lo copiaste completo.",
}


# ---------- /cuentas/seguridad/ ----------


@login_required
@require_http_methods(["GET", "POST"])
def seguridad(request):
    usuario = request.user
    form = ContrasenaActualForm(request.POST or None, usuario=usuario)
    codigos = None
    if request.method == "POST" and form.is_valid():
        accion = request.POST.get("accion")
        try:
            if accion == "correo":
                codigos = sf.activar_correo(usuario)
                messages.success(request, "Activaste la verificación en dos pasos por correo.")
            elif accion == "desactivar":
                sf.desactivar(usuario)
                messages.success(request, "Desactivaste la verificación en dos pasos.")
            elif accion == "respaldo":
                codigos = sf.regenerar_respaldo(usuario)
                messages.success(request, "Generamos 10 códigos de respaldo nuevos.")
            elif accion == "olvidar":
                sf.olvidar_dispositivos(usuario)
                messages.success(request, "Ningún dispositivo queda como de confianza.")
        except ValidationError as exc:
            form.add_error(None, exc.messages[0])
        else:
            if codigos:
                return render(
                    request,
                    "cuentas/codigos_respaldo.html",
                    {"codigos": codigos, "siguiente": "/cuentas/seguridad/"},
                )
            return redirect("cuentas:seguridad")
    contexto = {
        "form": form,
        "metodo": sf.de(usuario).metodo,
        "Metodo": SegundoFactor.Metodo,
        "obligatorio": sf.obligatorio(usuario),
        "respaldo": sf.respaldo_disponibles(usuario),
        "dispositivos": DispositivoConocido.objects.filter(usuario=usuario).order_by("-visto_en"),
    }
    return render(request, "cuentas/seguridad.html", contexto)


@login_required
@require_http_methods(["GET", "POST"])
def configurar_app(request):
    """Activa la app autenticadora: QR + contraseña + primer código."""
    secreto = request.session.setdefault("ap_totp_nuevo", sf.nuevo_secreto())
    form = ActivarAppForm(request.POST or None, usuario=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            codigos = sf.activar_app(
                request.user, secreto=secreto, codigo=form.cleaned_data["codigo"]
            )
        except ValidationError as exc:
            form.add_error("codigo", exc.messages[0])
        else:
            request.session.pop("ap_totp_nuevo", None)
            request.session[FLAG] = "verificado"  # acaba de demostrar el segundo factor
            messages.success(request, "Activaste la app autenticadora.")
            contexto = {"codigos": codigos, "siguiente": "/cuentas/seguridad/"}
            return render(request, "cuentas/codigos_respaldo.html", contexto)
    contexto = {
        "form": form,
        "qr": sf.qr_svg(sf.uri_totp(request.user, secreto)),
        "secreto": secreto,
    }
    return render(request, "cuentas/configurar_app.html", contexto)


class CambiarContrasenaView(auth.PasswordChangeView):
    """RF-25: al cambiarla llega un correo con «no fui yo»."""

    template_name = "cuentas/contrasena.html"
    success_url = reverse_lazy("cuentas:seguridad")

    def form_valid(self, form):
        respuesta = super().form_valid(form)  # guarda y conserva esta sesión
        correo.notificar_contrasena_cambiada(self.request.user)
        messages.success(self.request, "Tu contraseña cambió. Te enviamos un aviso por correo.")
        return respuesta


# ---------- RF-02: recuperar la contraseña (con el diseño y la cola de correo) ----------


class FormRecuperar(PasswordResetForm):
    def send_mail(self, *args, **kwargs):
        context = args[2] if len(args) > 2 else kwargs["context"]
        correo.enviar_recuperacion(context["user"])


class RecuperarView(auth.PasswordResetView):
    template_name = "cuentas/recuperar.html"
    form_class = FormRecuperar
    success_url = reverse_lazy("cuentas:recuperar_enviado")

    def form_valid(self, form):
        sujeto = form.cleaned_data["email"].lower()
        if not (
            permitir("recuperar-ip", ip_de(self.request), maximo=10, ventana_s=15 * 60)
            and permitir("recuperar-correo", sujeto, maximo=3, ventana_s=60 * 60)
        ):
            return redirect(self.success_url)  # misma respuesta: no revela nada
        return super().form_valid(form)


class RestablecerView(auth.PasswordResetConfirmView):
    template_name = "cuentas/restablecer.html"
    success_url = reverse_lazy("cuentas:restablecer_listo")

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        usuario = form.user
        if usuario.email and not usuario.email_verificado_en:  # demostró que el correo es suyo
            usuario.email_verificado_en = timezone.now()
            usuario.save(update_fields=["email_verificado_en"])
        correo.notificar_contrasena_cambiada(usuario)
        return respuesta


# ---------- RF-24: verificar el correo ----------


@require_http_methods(["GET", "POST"])
def verificar_correo(request, token: str):
    """GET muestra un botón; POST confirma. Así los antivirus que abren enlaces no lo gastan."""
    if request.method == "POST":
        try:
            correo.verificar_correo(token)
        except correo.EnlaceInvalidoError as exc:
            return render(
                request,
                "cuentas/enlace_resultado.html",
                {
                    "titulo": "No pudimos confirmar tu correo",
                    "mensaje": EXPLICACION_ENLACE[exc.motivo],
                },
                status=400,
            )
        messages.success(request, "¡Listo! Confirmamos tu correo.")
        destino = "cuentas:mis_datos" if request.user.is_authenticated else "cuentas:ingresar"
        return redirect(destino)
    return render(request, "cuentas/verificar_correo.html")


@login_required
@require_POST
def reenviar_verificacion(request):
    if permitir("verificacion", str(request.user.pk), maximo=3, ventana_s=60 * 60):
        correo.enviar_verificacion(request.user)
    messages.info(request, "Si tu correo aún no está confirmado, te enviamos un enlace nuevo.")
    return redirect(request.POST.get("volver") or "cuentas:mis_datos")


# ---------- RF-25: «no fui yo» ----------


@require_http_methods(["GET", "POST"])
def no_fui_yo(request, token: str):
    if request.method == "POST":
        try:
            usuario = correo.no_fui_yo(token)
        except correo.EnlaceInvalidoError as exc:
            mensaje = EXPLICACION_ENLACE[exc.motivo]
            return render(
                request,
                "cuentas/enlace_resultado.html",
                {"titulo": "El enlace ya no sirve", "mensaje": mensaje},
                status=400,
            )
        if request.user.is_authenticated and request.user.pk == usuario.pk:
            logout(request)
        return render(
            request,
            "cuentas/enlace_resultado.html",
            {
                "titulo": "Protegimos tu cuenta",
                "mensaje": "Bloqueamos la contraseña y cerramos las sesiones. Te enviamos un "
                "enlace para crear una contraseña nueva.",
                "exito": True,
            },
        )
    return render(request, "cuentas/no_fui_yo.html")


# ---------- Ley 1581: preferencias y baja de informativos ----------


@login_required
@require_POST
def preferencias(request):
    form = PreferenciasForm(request.POST)
    if form.is_valid():
        correo.cambiar_preferencias(
            usuario=request.user, informativos=form.cleaned_data["correos_informativos"]
        )
        messages.success(request, "Guardamos tus preferencias de correo.")
    return redirect("cuentas:mis_datos")


@csrf_exempt  # List-Unsubscribe-Post (RFC 8058): el cliente de correo envía un POST sin sesión
@require_http_methods(["GET", "POST"])
def baja(request, token: str):
    if request.method == "POST":
        try:
            correo.dar_de_baja(token)
        except correo.EnlaceInvalidoError:
            return render(
                request,
                "cuentas/enlace_resultado.html",
                {"titulo": "El enlace no es válido", "mensaje": EXPLICACION_ENLACE["invalido"]},
                status=400,
            )
        return render(
            request,
            "cuentas/enlace_resultado.html",
            {
                "titulo": "Listo: no recibirás más correos informativos",
                "mensaje": "Los correos de seguridad seguirán llegando porque protegen tu cuenta. "
                "Puedes volver a activarlos en Mis datos.",
                "exito": True,
            },
        )
    return render(request, "cuentas/baja.html")
