"""Correos de la cuenta (RF-24, RF-25, RF-27): enlaces firmados y avisos de seguridad.

Los enlaces son firmados con la SECRET_KEY y de un solo uso: el contenido firmado incluye un dato
que cambia al usarlos (correo verificado, contraseña), así un enlace usado deja de servir.
Nunca se guardan en la cola: se regeneran si hay que reintentar (ver `registrar_en_notificaciones`).
"""

from datetime import timedelta

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.formats import date_format
from django.utils.http import urlsafe_base64_encode

from apps.notificaciones import services as notificaciones
from apps.notificaciones.domain.catalogo import Tipo
from apps.notificaciones.models import CorreoPendiente

from ..domain.dispositivos import describir_navegador, huella_dispositivo
from ..models import DispositivoConocido, SegundoFactor, Usuario

VIGENCIA_VERIFICACION = timedelta(hours=24)
VIGENCIA_NO_FUI_YO = timedelta(days=7)
_SAL_VERIFICAR = "cuentas.verificar-correo"
_SAL_NO_FUI_YO = "cuentas.no-fui-yo"
_SAL_BAJA = "cuentas.baja-informativos"


class EnlaceInvalidoError(Exception):
    """El enlace venció, ya se usó o fue alterado."""

    def __init__(self, motivo: str):
        super().__init__(motivo)
        self.motivo = motivo  # "vencido" | "usado" | "invalido"


def _cuando(momento=None) -> str:
    return date_format(timezone.localtime(momento or timezone.now()), "j \\d\\e F \\d\\e Y, H:i")


def _url(ruta: str) -> str:
    return f"{settings.SITIO_URL}{ruta}"


def _leer(token: str, *, sal: str, vigencia: timedelta) -> dict:
    try:
        return signing.loads(token, salt=sal, max_age=vigencia)
    except signing.SignatureExpired as exc:
        raise EnlaceInvalidoError("vencido") from exc
    except signing.BadSignature as exc:
        raise EnlaceInvalidoError("invalido") from exc


# ---------- RF-24: verificación del correo ----------


def enlace_verificacion(usuario: Usuario) -> str:
    datos = {"u": usuario.pk, "e": usuario.email.lower(), "v": bool(usuario.email_verificado_en)}
    return _url(f"/cuentas/verificar-correo/{signing.dumps(datos, salt=_SAL_VERIFICAR)}/")


ESPERA_REENVIO = timedelta(minutes=1)


def _verificacion_reciente(usuario: Usuario) -> bool:
    """Un doble clic o un formulario enviado dos veces no debe producir dos correos."""
    desde = timezone.now() - ESPERA_REENVIO
    return CorreoPendiente.objects.filter(
        usuario=usuario,
        tipo=Tipo.VERIFICAR_CORREO,
        destinatario__iexact=usuario.email,
        creado_en__gte=desde,
    ).exists()


def enviar_verificacion(usuario: Usuario) -> None:
    if not usuario.email or usuario.email_verificado_en or _verificacion_reciente(usuario):
        return
    notificaciones.encolar(
        tipo=Tipo.VERIFICAR_CORREO,
        usuario=usuario,
        clave_idempotencia=notificaciones.nueva_clave("verificar", usuario.pk),
        efimero={"enlace": enlace_verificacion(usuario)},
    )


@transaction.atomic
def verificar_correo(token: str) -> Usuario:
    """Marca el correo como verificado (una sola vez, máximo 24 h) y envía la bienvenida."""
    datos = _leer(token, sal=_SAL_VERIFICAR, vigencia=VIGENCIA_VERIFICACION)
    usuario = Usuario.objects.select_for_update().filter(pk=datos.get("u")).first()
    if usuario is None or usuario.email.lower() != datos.get("e"):
        raise EnlaceInvalidoError("invalido")  # el correo cambió después de enviar el enlace
    if usuario.email_verificado_en or datos.get("v"):
        raise EnlaceInvalidoError("usado")
    usuario.email_verificado_en = timezone.now()
    usuario.save(update_fields=["email_verificado_en"])
    notificaciones.encolar(
        tipo=Tipo.BIENVENIDA, usuario=usuario, clave_idempotencia=f"bienvenida:{usuario.pk}"
    )
    return usuario


# ---------- RF-02: recuperar la contraseña ----------


def enlace_recuperacion(usuario: Usuario) -> str:
    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
    token = default_token_generator.make_token(usuario)
    return _url(f"/cuentas/contrasena/restablecer/{uid}/{token}/")


def enviar_recuperacion(usuario: Usuario) -> None:
    notificaciones.encolar(
        tipo=Tipo.RECUPERAR_CONTRASENA,
        usuario=usuario,
        clave_idempotencia=notificaciones.nueva_clave("recuperar", usuario.pk),
        efimero={"enlace": enlace_recuperacion(usuario)},
    )


# ---------- RF-25: contraseña cambiada y «no fui yo» ----------


def _sello_contrasena(usuario: Usuario) -> str:
    return usuario.password[-12:]  # cambia con cada contraseña nueva: el enlace caduca


def enlace_no_fui_yo(usuario: Usuario) -> str:
    datos = {"u": usuario.pk, "p": _sello_contrasena(usuario)}
    return _url(f"/cuentas/no-fui-yo/{signing.dumps(datos, salt=_SAL_NO_FUI_YO)}/")


def notificar_contrasena_cambiada(usuario: Usuario) -> None:
    notificaciones.encolar(
        tipo=Tipo.CONTRASENA_CAMBIADA,
        usuario=usuario,
        clave_idempotencia=notificaciones.nueva_clave("contrasena", usuario.pk),
        contexto={"cuando": _cuando()},
        efimero={"enlace": enlace_no_fui_yo(usuario)},
    )


@transaction.atomic
def no_fui_yo(token: str) -> Usuario:
    """Bloquea la contraseña, invalida las sesiones y los dispositivos de confianza y envía un
    enlace para crear una contraseña nueva."""
    datos = _leer(token, sal=_SAL_NO_FUI_YO, vigencia=VIGENCIA_NO_FUI_YO)
    usuario = Usuario.objects.select_for_update().filter(pk=datos.get("u")).first()
    if usuario is None or _sello_contrasena(usuario) != datos.get("p"):
        raise EnlaceInvalidoError("usado")
    usuario.set_unusable_password()  # también cierra las sesiones (cambia el hash de sesión)
    usuario.save(update_fields=["password"])
    SegundoFactor.objects.filter(usuario=usuario).update(
        version_confianza=F("version_confianza") + 1
    )
    # Directo, no por el formulario de Django: ese no envía a cuentas sin contraseña usable
    enviar_recuperacion(usuario)
    return usuario


# ---------- RF-25: ingreso desde un dispositivo nuevo ----------


def registrar_dispositivo(usuario: Usuario, *, user_agent: str, ip: str) -> bool:
    """Guarda la huella. True (y avisa por correo) si es nuevo y la cuenta ya tenía otros."""
    huella = huella_dispositivo(user_agent=user_agent, ip=ip, clave=settings.SECRET_KEY)
    navegador = describir_navegador(user_agent)
    tenia_otros = DispositivoConocido.objects.filter(usuario=usuario).exists()
    dispositivo, creado = DispositivoConocido.objects.get_or_create(
        usuario=usuario, huella=huella, defaults={"navegador": navegador}
    )
    if not creado:
        dispositivo.save(update_fields=["visto_en"])
        return False
    if tenia_otros:
        notificaciones.encolar(
            tipo=Tipo.NUEVO_DISPOSITIVO,
            usuario=usuario,
            clave_idempotencia=f"dispositivo:{usuario.pk}:{dispositivo.pk}",
            contexto={"navegador": navegador, "cuando": _cuando()},
        )
    return tenia_otros


# ---------- RF-22 y RF-03: suspensión y supresión ----------


def notificar_suspension(usuario: Usuario) -> None:
    notificaciones.encolar(
        tipo=Tipo.CUENTA_SUSPENDIDA,
        usuario=usuario,
        clave_idempotencia=notificaciones.nueva_clave("suspendida", usuario.pk),
    )


def notificar_supresion(usuario: Usuario) -> None:
    """Se llama ANTES de borrar el correo; la cola lo redacta en cuanto se envía."""
    notificaciones.encolar(
        tipo=Tipo.CUENTA_SUPRIMIDA,
        destinatario=usuario.email,
        clave_idempotencia=notificaciones.nueva_clave("suprimida", usuario.pk),
        contexto={"nombre": usuario.username},
    )


# ---------- Ley 1581: baja de los correos informativos ----------


def enlace_baja(usuario: Usuario) -> str:
    return _url(f"/cuentas/correo/baja/{signing.dumps({'u': usuario.pk}, salt=_SAL_BAJA)}/")


def dar_de_baja(token: str) -> Usuario:
    try:
        datos = signing.loads(token, salt=_SAL_BAJA)  # sin vencimiento: la baja siempre sirve
    except signing.BadSignature as exc:
        raise EnlaceInvalidoError("invalido") from exc
    usuario = Usuario.objects.filter(pk=datos.get("u")).first()
    if usuario is None:
        raise EnlaceInvalidoError("invalido")
    cambiar_preferencias(usuario=usuario, informativos=False)
    return usuario


def cambiar_preferencias(*, usuario: Usuario, informativos: bool) -> Usuario:
    usuario.correos_informativos = informativos
    usuario.save(update_fields=["correos_informativos"])
    return usuario


# ---------- Reintentos: los enlaces firmados se regeneran, nunca se guardan ----------


def registrar_en_notificaciones() -> None:
    def con_usuario(funcion):
        def regenerar(correo):
            return {"enlace": funcion(correo.usuario)} if correo.usuario else None

        return regenerar

    notificaciones.registrar_regenerador(Tipo.VERIFICAR_CORREO, con_usuario(enlace_verificacion))
    notificaciones.registrar_regenerador(
        Tipo.RECUPERAR_CONTRASENA, con_usuario(enlace_recuperacion)
    )
    notificaciones.registrar_regenerador(Tipo.CONTRASENA_CAMBIADA, con_usuario(enlace_no_fui_yo))
    notificaciones.registrar_enlace_baja(enlace_baja)
