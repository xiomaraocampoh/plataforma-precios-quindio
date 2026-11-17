"""Verificación en dos pasos (RF-27, ADR-021): correo, app autenticadora (TOTP) y respaldo.

Las reglas (vigencia, intentos, bloqueo) están en apps.cuentas.domain.segundo_factor; aquí solo
se leen y guardan los datos. pyotp implementa TOTP (RFC 6238) y qrcode dibuja el QR en SVG.
"""

import hmac
import io

import pyotp
import qrcode
import qrcode.image.svg
from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.notificaciones import services as notificaciones
from apps.notificaciones.domain.catalogo import Tipo

from ..domain.segundo_factor import (
    VIGENCIA_CODIGO,
    EstadoIntentos,
    Resultado,
    buscar_respaldo,
    coincide,
    evaluar,
    generar_codigo,
    generar_codigos_respaldo,
    hash_codigo,
    omitir_segundo_factor_de_prueba,
    pedir_segundo_factor,
    segundo_factor_obligatorio,
)
from ..models import CodigoRespaldo, SegundoFactor, Usuario

EMISOR = "AhorraPues"
DIAS_CONFIANZA = 30
COOKIE_CONFIANZA = "ap_confianza"
_SAL_CONFIANZA = "cuentas.dispositivo-confianza"
Metodo = SegundoFactor.Metodo


def _clave() -> str:
    return settings.SECRET_KEY


def de(usuario: Usuario) -> SegundoFactor:
    return SegundoFactor.objects.get_or_create(usuario=usuario)[0]


def obligatorio(usuario: Usuario) -> bool:
    return segundo_factor_obligatorio(
        rol=usuario.rol, es_staff=usuario.is_staff, es_superusuario=usuario.is_superuser
    )


def exento_por_prueba(usuario: Usuario) -> bool:
    """Cuenta de prueba en local con PERMITIR_PRUEBA_SIN_2FA y DEBUG=True (nunca en producción)."""
    return omitir_segundo_factor_de_prueba(
        permitido=getattr(settings, "PERMITIR_PRUEBA_SIN_2FA", False),
        debug=settings.DEBUG,
        es_cuenta_de_prueba=getattr(usuario, "es_cuenta_prueba", False),
    )


def activado(usuario: Usuario) -> bool:
    return de(usuario).metodo != Metodo.NINGUNO


def puede_usar_correo(usuario: Usuario) -> bool:
    return bool(usuario.email)


def necesita_inscribirse(usuario: Usuario) -> bool:
    """Obligatoria, sin app configurada y sin correo: debe configurar la app al ingresar."""
    return obligatorio(usuario) and de(usuario).metodo != Metodo.APP and not usuario.email


def pide_segundo_paso(usuario: Usuario, cookie_confianza: str | None) -> bool:
    return pedir_segundo_factor(
        obligatorio=obligatorio(usuario),
        activado=activado(usuario),
        dispositivo_de_confianza=es_de_confianza(usuario, cookie_confianza),
    )


def exigir_contrasena(usuario: Usuario, contrasena: str) -> None:
    if not contrasena or not check_password(contrasena, usuario.password):
        raise ValidationError("La contraseña no es correcta.")


# ---------- Código por correo ----------


def enviar_codigo(usuario: Usuario, *, proposito: str = "ingresar a tu cuenta") -> bool:
    """Genera un código de 6 dígitos (vence en 10 min) y lo envía. Solo se guarda su hash."""
    if not puede_usar_correo(usuario):
        return False
    codigo = generar_codigo()
    sf = de(usuario)
    sf.codigo_hash = hash_codigo(codigo, clave=_clave())
    sf.codigo_vence_en = timezone.now() + VIGENCIA_CODIGO
    sf.save(update_fields=["codigo_hash", "codigo_vence_en", "actualizado_en"])
    notificaciones.encolar(
        tipo=Tipo.CODIGO_VERIFICACION,
        usuario=usuario,
        clave_idempotencia=notificaciones.nueva_clave("codigo", usuario.pk),
        contexto={"proposito": proposito},
        efimero={"codigo": codigo},
    )
    return True


# ---------- Verificar (correo, app o respaldo) con la política de intentos ----------


def _limpio(codigo: str) -> str:
    return "".join(codigo.split()).replace("-", "")


def _es_respaldo(codigo: str) -> bool:
    """Respaldo: 8 caracteres (abcd-efgh). Correo y app: 6 dígitos."""
    return len(_limpio(codigo)) == 8


def _usar_respaldo(usuario: Usuario, codigo: str) -> bool:
    disponibles = list(CodigoRespaldo.objects.filter(usuario=usuario, usado_en__isnull=True))
    posicion = buscar_respaldo(codigo, [c.codigo_hash for c in disponibles], clave=_clave())
    if posicion is None:
        return False
    disponibles[posicion].usado_en = timezone.now()
    disponibles[posicion].save(update_fields=["usado_en"])
    return True


def _usar_totp(sf: SegundoFactor, codigo: str, ahora) -> bool:
    if sf.metodo != Metodo.APP or not sf.totp_secreto:
        return False
    totp = pyotp.TOTP(sf.totp_secreto)
    paso = totp.timecode(ahora)
    for desfase in (0, -1, 1):  # ±30 s por relojes desfasados
        candidato = paso + desfase
        if sf.totp_ultimo_paso is not None and candidato <= sf.totp_ultimo_paso:
            continue  # un código TOTP sirve una sola vez
        if hmac.compare_digest(totp.generate_otp(candidato), _limpio(codigo)):
            sf.totp_ultimo_paso = candidato
            return True
    return False


def _usar_codigo_correo(sf: SegundoFactor, codigo: str, ahora) -> bool:
    vigente = sf.codigo_vence_en and ahora <= sf.codigo_vence_en
    if vigente and coincide(codigo, sf.codigo_hash, clave=_clave()):
        sf.codigo_hash, sf.codigo_vence_en = "", None  # un solo uso
        return True
    return False


@transaction.atomic
def verificar(usuario: Usuario, codigo: str) -> Resultado:
    """Comprueba el segundo factor con máximo 5 intentos y 15 min de bloqueo (dominio)."""
    sf = SegundoFactor.objects.select_for_update().get(pk=de(usuario).pk)
    ahora = timezone.now()
    codigo = (codigo or "").strip()
    vencido = (
        not _es_respaldo(codigo)
        and sf.codigo_vence_en is not None
        and ahora > sf.codigo_vence_en
        and coincide(codigo, sf.codigo_hash, clave=_clave())
    )

    def es_correcto() -> bool:
        if _es_respaldo(codigo):
            return _usar_respaldo(usuario, codigo)
        return _usar_totp(sf, codigo, ahora) or _usar_codigo_correo(sf, codigo, ahora)

    estado = EstadoIntentos(sf.intentos_fallidos, sf.bloqueado_hasta)
    resultado, nuevo = evaluar(es_correcto=es_correcto, estado=estado, ahora=ahora, vence_en=None)
    if vencido and resultado == Resultado.INCORRECTO:
        resultado = Resultado.VENCIDO  # el código era el correcto, pero ya pasó su tiempo
    sf.intentos_fallidos, sf.bloqueado_hasta = nuevo.intentos_fallidos, nuevo.bloqueado_hasta
    sf.save()
    return resultado


# ---------- Configurar la app autenticadora ----------


def nuevo_secreto() -> str:
    return pyotp.random_base32()


def uri_totp(usuario: Usuario, secreto: str) -> str:
    return pyotp.TOTP(secreto).provisioning_uri(name=usuario.username, issuer_name=EMISOR)


def qr_svg(texto: str) -> str:
    """QR en SVG (sin imágenes externas ni dependencias gráficas)."""
    imagen = qrcode.make(texto, image_factory=qrcode.image.svg.SvgPathImage, box_size=8, border=2)
    salida = io.BytesIO()
    imagen.save(salida)
    svg = salida.getvalue().decode()
    return svg[svg.index("<svg") :]  # sin la declaración XML: va incrustado en el HTML


@transaction.atomic
def activar_app(usuario: Usuario, *, secreto: str, codigo: str) -> list[str]:
    """Confirma el primer código de la app y la deja como método. Devuelve 10 códigos de respaldo
    (se muestran una sola vez)."""
    if not pyotp.TOTP(secreto).verify((codigo or "").replace(" ", ""), valid_window=1):
        raise ValidationError(
            "El código no coincide. Revisa la hora del celular e inténtalo de nuevo."
        )
    sf = de(usuario)
    sf.metodo, sf.totp_secreto, sf.totp_ultimo_paso = Metodo.APP, secreto, None
    sf.save()
    return regenerar_respaldo(usuario)


def activar_correo(usuario: Usuario) -> list[str]:
    if not usuario.email_verificado_en:
        raise ValidationError("Primero confirma tu correo: ahí llegarán los códigos.")
    sf = de(usuario)
    sf.metodo, sf.totp_secreto = Metodo.CORREO, ""
    sf.save()
    return regenerar_respaldo(usuario)


@transaction.atomic
def desactivar(usuario: Usuario) -> None:
    if obligatorio(usuario):
        raise ValidationError(
            "Tu rol exige la verificación en dos pasos: puedes cambiar de método, no quitarla."
        )
    SegundoFactor.objects.filter(usuario=usuario).update(
        metodo=Metodo.NINGUNO,
        totp_secreto="",
        totp_ultimo_paso=None,
        version_confianza=F("version_confianza") + 1,
    )
    CodigoRespaldo.objects.filter(usuario=usuario).delete()


def regenerar_respaldo(usuario: Usuario) -> list[str]:
    codigos = generar_codigos_respaldo()
    CodigoRespaldo.objects.filter(usuario=usuario).delete()
    CodigoRespaldo.objects.bulk_create(
        CodigoRespaldo(usuario=usuario, codigo_hash=hash_codigo(c, clave=_clave())) for c in codigos
    )
    return codigos


def respaldo_disponibles(usuario: Usuario) -> int:
    return CodigoRespaldo.objects.filter(usuario=usuario, usado_en__isnull=True).count()


# ---------- «Confiar en este dispositivo 30 días» (cookie firmada) ----------


def firmar_confianza(usuario: Usuario) -> str:
    return signing.dumps({"u": usuario.pk, "v": de(usuario).version_confianza}, salt=_SAL_CONFIANZA)


def es_de_confianza(usuario: Usuario, valor: str | None) -> bool:
    if not valor:
        return False
    try:
        datos = signing.loads(valor, salt=_SAL_CONFIANZA, max_age=DIAS_CONFIANZA * 86400)
    except signing.BadSignature:
        return False
    return datos.get("u") == usuario.pk and datos.get("v") == de(usuario).version_confianza


def olvidar_dispositivos(usuario: Usuario) -> None:
    SegundoFactor.objects.filter(usuario=usuario).update(
        version_confianza=F("version_confianza") + 1
    )
