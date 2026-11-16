"""Envío de correo transaccional con outbox (ADR-021). Capa de aplicación.

Flujo: `encolar` guarda la fila y, al confirmarse la transacción, intenta enviarla enseguida. Si
el SMTP falla, queda pendiente y `manage.py enviar_correos` la reintenta (máximo 3 veces, con
espera creciente). El envío «reclama» la fila con un UPDATE condicional: dos procesos nunca envían
el mismo correo.

Este módulo no conoce a cuentas ni a moderación: quien necesita regenerar un enlace firmado en un
reintento registra un «regenerador» (inversión de dependencias, ver apps.cuentas.apps).
"""

import logging
import re
import uuid
from collections.abc import Callable
from datetime import timedelta
from email.utils import make_msgid
from urllib.parse import urlsplit

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.db.models import F
from django.template.loader import render_to_string
from django.utils import timezone

from .domain.catalogo import Categoria, Tipo, categoria_de, contexto_persistible, debe_enviarse
from .domain.privacidad import enmascarar_correo
from .domain.reintentos import MAX_INTENTOS, puede_reintentar
from .models import CorreoPendiente

log = logging.getLogger("ahorrapues.correo")
Estado = CorreoPendiente.Estado

# Tipos cuyo correo lleva un secreto (enlace firmado o código) que no se guarda en la cola
TIPOS_CON_SECRETO = frozenset(
    {
        Tipo.VERIFICAR_CORREO,
        Tipo.RECUPERAR_CONTRASENA,
        Tipo.CONTRASENA_CAMBIADA,
        Tipo.CODIGO_VERIFICACION,
    }
)
# Tras el último intento se borra la dirección: la persona pidió suprimir sus datos (RF-03)
TIPOS_QUE_SE_REDACTAN = frozenset({Tipo.CUENTA_SUPRIMIDA})
ENVIANDO_INCIERTO = timedelta(minutes=10)

_regeneradores: dict[str, Callable[[CorreoPendiente], dict]] = {}
_enlace_baja: list[Callable[[object], str]] = []
_CORREO = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")


def registrar_regenerador(tipo: str, funcion: Callable[[CorreoPendiente], dict]) -> None:
    """`funcion(correo)` devuelve los datos secretos de nuevo (p. ej. un enlace firmado nuevo)."""
    _regeneradores[str(tipo)] = funcion


def registrar_enlace_baja(funcion: Callable[[object], str]) -> None:
    """`funcion(usuario)` devuelve la URL firmada para dejar de recibir informativos."""
    _enlace_baja[:] = [funcion]


# ---------- Encolar ----------


def encolar(
    *,
    tipo: str,
    clave_idempotencia: str,
    usuario=None,
    destinatario: str = "",
    contexto: dict | None = None,
    efimero: dict | None = None,
) -> CorreoPendiente | None:
    """Agrega un correo a la cola si corresponde. Devuelve None si no debe enviarse.

    `efimero` (código, enlace) solo vive en memoria para el primer intento; nunca va a la BD.
    La misma `clave_idempotencia` devuelve la fila existente: un evento, un correo.
    """
    destinatario = (destinatario or getattr(usuario, "email", "") or "").strip()
    if not debe_enviarse(
        tipo=tipo,
        tiene_correo=bool(destinatario),
        correo_verificado=bool(getattr(usuario, "email_verificado_en", None)),
        acepta_informativos=getattr(usuario, "correos_informativos", True),
    ):
        return None
    correo, creado = CorreoPendiente.objects.get_or_create(
        clave_idempotencia=clave_idempotencia[:150],
        defaults={
            "usuario": usuario,
            "destinatario": destinatario,
            "tipo": str(tipo),
            "contexto": contexto_persistible(contexto or {}),
        },
    )
    if not creado:
        return correo
    if settings.NOTIFICACIONES["ENVIAR_AL_CONFIRMAR"]:
        transaction.on_commit(lambda: enviar(correo.pk, efimero=efimero))
    else:
        enviar(correo.pk, efimero=efimero)
    return correo


def nueva_clave(*partes) -> str:
    """Clave de idempotencia para un evento que puede repetirse (cada reenvío es un evento)."""
    return ":".join(str(p) for p in (*partes, uuid.uuid4().hex))


# ---------- Renderizar ----------


def _host_del_sitio() -> str:
    return urlsplit(settings.SITIO_URL).hostname or "ahorrapues.local"


def _enlace_producto(datos: dict) -> str:
    producto = datos.get("producto_id")
    return f"{settings.SITIO_URL}/productos/{producto}/" if producto else ""


def contexto_base(tipo: str, datos: dict, usuario=None) -> dict:
    informativo = categoria_de(tipo) == Categoria.INFORMATIVO
    enlace_baja = _enlace_baja[0](usuario) if informativo and usuario and _enlace_baja else ""
    return {
        **datos,
        "tipo": str(tipo),
        "informativo": informativo,
        "sitio_url": settings.SITIO_URL,
        "enlace_preferencias": f"{settings.SITIO_URL}/cuentas/mis-datos/#preferencias",
        "enlace_recuperar": f"{settings.SITIO_URL}/cuentas/contrasena/recuperar/",
        "enlace_registrar": f"{settings.SITIO_URL}/precios/registrar/",
        "enlace_aportes": f"{settings.SITIO_URL}/precios/mis-aportes/",
        "enlace_directorio": f"{settings.SITIO_URL}/establecimientos/",
        "enlace_producto": _enlace_producto(datos),
        "enlace_baja": enlace_baja,
        "nombre": datos.get("nombre") or getattr(usuario, "username", "") or "",
    }


def renderizar(tipo: str, datos: dict, usuario=None) -> tuple[str, str, str]:
    """(asunto, texto, html) de la plantilla `correo/<tipo>/`."""
    contexto = contexto_base(tipo, datos, usuario)
    asunto = " ".join(render_to_string(f"correo/{tipo}/asunto.txt", contexto).split())
    contexto["asunto"] = asunto
    texto = render_to_string(f"correo/{tipo}/cuerpo.txt", contexto).strip() + "\n"
    html = render_to_string(f"correo/{tipo}/cuerpo.html", contexto)
    return asunto, texto, html


def _mensaje(correo: CorreoPendiente, datos: dict) -> EmailMultiAlternatives:
    asunto, texto, html = renderizar(correo.tipo, datos, correo.usuario)
    correo.message_id = make_msgid(idstring=f"correo{correo.pk}", domain=_host_del_sitio())
    cabeceras = {"Message-ID": correo.message_id}
    if categoria_de(correo.tipo) == Categoria.INFORMATIVO and _enlace_baja and correo.usuario:
        cabeceras["List-Unsubscribe"] = f"<{_enlace_baja[0](correo.usuario)}>"
        cabeceras["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
    mensaje = EmailMultiAlternatives(
        subject=asunto,
        body=texto,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[correo.destinatario],
        reply_to=[settings.EMAIL_REPLY_TO] if settings.EMAIL_REPLY_TO else None,
        headers=cabeceras,
    )
    mensaje.attach_alternative(html, "text/html")
    return mensaje


# ---------- Enviar ----------


def _reclamar(correo_id: int) -> bool:
    """PENDIENTE → ENVIANDO en un solo UPDATE: solo un proceso gana; los demás no envían."""
    return bool(
        CorreoPendiente.objects.filter(
            pk=correo_id, estado=Estado.PENDIENTE, intentos__lt=MAX_INTENTOS
        ).update(estado=Estado.ENVIANDO, intentos=F("intentos") + 1, ultimo_intento=timezone.now())
    )


def _datos_secretos(correo: CorreoPendiente, efimero: dict | None) -> dict | None:
    if efimero:
        return efimero
    if correo.tipo not in TIPOS_CON_SECRETO:
        return {}
    regenerar = _regeneradores.get(correo.tipo)
    return regenerar(correo) if regenerar else None


def _sin_correos(texto: str) -> str:
    return _CORREO.sub("[correo]", texto)[:300]


def _terminar(correo: CorreoPendiente, estado: str, error: str = "") -> None:
    correo.estado = estado
    correo.error = _sin_correos(error)
    campos = ["estado", "error", "message_id", "enviado_en", "destinatario", "contexto"]
    if estado == Estado.ENVIADO:
        correo.enviado_en = timezone.now()
    final = estado in (Estado.ENVIADO, Estado.FALLIDO)
    if final and correo.tipo in TIPOS_QUE_SE_REDACTAN:
        correo.destinatario, correo.contexto = "", {}
    correo.save(update_fields=campos)


def enviar(correo_id: int, *, efimero: dict | None = None) -> bool:
    """Un intento de envío. True si salió. Nunca lanza: el error queda en la fila."""
    if not _reclamar(correo_id):
        return False
    correo = CorreoPendiente.objects.select_related("usuario").get(pk=correo_id)
    secretos = _datos_secretos(correo, efimero)
    if secretos is None:  # un código de un solo uso no se puede regenerar: se pide otro
        _terminar(correo, Estado.FALLIDO, "Lleva un código de un solo uso: hay que pedir otro.")
        log.warning("correo #%s %s no reintentable", correo.pk, correo.tipo)
        return False
    try:
        _mensaje(correo, {**correo.contexto, **secretos}).send(fail_silently=False)
    except Exception as exc:  # SMTP, red, TLS: se reintenta más tarde
        agotado = correo.intentos >= MAX_INTENTOS
        siguiente = Estado.FALLIDO if agotado else Estado.PENDIENTE
        _terminar(correo, siguiente, f"{type(exc).__name__}: {exc}")
        log.warning(
            "correo #%s %s a %s falló (intento %s/%s): %s",
            correo.pk,
            correo.tipo,
            enmascarar_correo(correo.destinatario),
            correo.intentos,
            MAX_INTENTOS,
            type(exc).__name__,
        )
        return False
    destino = enmascarar_correo(correo.destinatario)
    _terminar(correo, Estado.ENVIADO)
    log.info("correo #%s %s enviado a %s", correo.pk, correo.tipo, destino)
    return True


def enviar_pendientes(ahora=None) -> dict[str, int]:
    """Reintenta lo pendiente que ya esperó lo suficiente. Lo usa `manage.py enviar_correos`."""
    ahora = ahora or timezone.now()
    inciertos = CorreoPendiente.objects.filter(
        estado=Estado.ENVIANDO, ultimo_intento__lt=ahora - ENVIANDO_INCIERTO
    ).update(estado=Estado.FALLIDO, error="Estado incierto: no se reintenta para no duplicarlo.")
    enviados = fallidos = 0
    for correo in CorreoPendiente.objects.filter(estado=Estado.PENDIENTE).order_by("pk"):
        if not puede_reintentar(
            intentos=correo.intentos, ultimo_intento=correo.ultimo_intento, ahora=ahora
        ):
            continue
        if enviar(correo.pk):
            enviados += 1
        else:
            fallidos += 1
    return {"enviados": enviados, "fallidos": fallidos, "inciertos": inciertos}
