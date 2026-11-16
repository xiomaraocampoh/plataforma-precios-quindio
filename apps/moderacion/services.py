"""Casos de uso de moderación (RF-20, RF-21, RF-22).

Orquesta los servicios de cada módulo (nunca escribe en el ORM de otro módulo) y registra cada
decisión con el moderador y la fecha en `DecisionModeracion`.
"""

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.catalogo import services as catalogo
from apps.cuentas import services as cuentas
from apps.establecimientos import services as establecimientos
from apps.notificaciones import services as notificaciones
from apps.notificaciones.domain.catalogo import Tipo
from apps.precios import services as precios
from apps.precios.models import ReportePrecio

from .models import DecisionModeracion, Denuncia
from .permisos import es_moderador

Accion = DecisionModeracion.Accion


class DenunciaDuplicadaError(Exception):
    """RF-20: una sola denuncia por usuario y reporte."""


class SinPermisoDeModeracionError(PermissionError):
    pass


def denunciar(*, denunciante, reporte_id: int, motivo: str, detalle: str = "") -> Denuncia:
    reporte = ReportePrecio.objects.filter(
        pk=reporte_id, estado=ReportePrecio.Estado.PUBLICADO
    ).first()
    if reporte is None:
        raise ValidationError("El precio no existe o no está publicado.")
    if reporte.autor_id == denunciante.pk:
        raise ValidationError("No puedes denunciar un precio que reportaste tú.")
    if motivo not in Denuncia.Motivo.values:
        raise ValidationError("Elige un motivo válido.")
    try:
        with transaction.atomic():
            return Denuncia.objects.create(
                reporte=reporte, denunciante=denunciante, motivo=motivo, detalle=detalle.strip()
            )
    except IntegrityError as exc:  # UniqueConstraint una_denuncia_por_usuario
        raise DenunciaDuplicadaError("Ya denunciaste este precio.") from exc


def _exigir_moderador(moderador) -> None:
    if not es_moderador(moderador):
        raise SinPermisoDeModeracionError("Solo moderación puede tomar esta decisión.")


def _registrar(moderador, accion: str, tipo: str, objeto_id: int, motivo: str):
    return DecisionModeracion.objects.create(
        moderador=moderador,
        accion=accion,
        objeto_tipo=tipo,
        objeto_id=objeto_id,
        motivo=motivo.strip(),
    )


# ---------- RF-26: avisos de moderación (informativos; nunca dicen quién denunció ni moderó) ----


def _avisar(tipo: str, usuario, clave: str, **contexto) -> None:
    if usuario is not None:
        notificaciones.encolar(
            tipo=tipo, usuario=usuario, clave_idempotencia=clave, contexto=contexto
        )


def _pesos(valor) -> str:
    return f"{valor:,.0f}".replace(",", ".")


def _avisar_reporte(reporte_id: int, aprobado: bool) -> None:
    r = ReportePrecio.objects.select_related(
        "autor", "presentacion__producto__marca", "establecimiento"
    ).get(pk=reporte_id)
    _avisar(
        Tipo.REPORTE_MODERADO,
        r.autor,
        f"reporte_moderado:{r.pk}",
        aprobado=aprobado,
        presentacion=str(r.presentacion),
        precio=_pesos(r.precio),
        establecimiento=r.establecimiento.nombre,
    )


def _avisar_denuncia(denuncia: Denuncia, aceptada: bool) -> None:
    r = ReportePrecio.objects.select_related(
        "presentacion__producto__marca", "establecimiento"
    ).get(pk=denuncia.reporte_id)
    _avisar(
        Tipo.DENUNCIA_RESUELTA,
        denuncia.denunciante,
        f"denuncia_resuelta:{denuncia.pk}",
        aprobado=aceptada,
        producto=str(r.presentacion),
        producto_id=r.presentacion.producto_id,
        establecimiento=r.establecimiento.nombre,
    )


@transaction.atomic
def decidir_reporte(*, moderador, reporte_id: int, aprobar: bool, motivo: str = ""):
    _exigir_moderador(moderador)
    precios.resolver_revision(reporte_id=reporte_id, aprobar=aprobar)
    _avisar_reporte(reporte_id, aprobar)
    accion = Accion.APROBAR_REPORTE if aprobar else Accion.RECHAZAR_REPORTE
    return _registrar(moderador, accion, "reporte", reporte_id, motivo)


@transaction.atomic
def resolver_denuncia(*, moderador, denuncia_id: int, aceptar: bool, motivo: str = ""):
    _exigir_moderador(moderador)
    denuncia = Denuncia.objects.select_for_update().get(pk=denuncia_id)
    if denuncia.estado != Denuncia.Estado.ABIERTA:
        raise ValidationError("La denuncia ya fue resuelta.")
    denuncia.estado = Denuncia.Estado.ACEPTADA if aceptar else Denuncia.Estado.DESCARTADA
    denuncia.resuelto_por = moderador
    denuncia.resuelto_en = timezone.now()
    denuncia.save(update_fields=["estado", "resuelto_por", "resuelto_en"])
    if aceptar:
        precios.retirar_reporte(reporte_id=denuncia.reporte_id)
    _avisar_denuncia(denuncia, aceptar)
    accion = Accion.ACEPTAR_DENUNCIA if aceptar else Accion.DESCARTAR_DENUNCIA
    return _registrar(moderador, accion, "denuncia", denuncia_id, motivo)


@transaction.atomic
def decidir_solicitud(*, moderador, solicitud_id: int, aprobar: bool, motivo: str = ""):
    _exigir_moderador(moderador)
    if aprobar:
        solicitud = catalogo.aprobar_solicitud(solicitud_id=solicitud_id, moderador=moderador)
    else:
        solicitud = catalogo.rechazar_solicitud(solicitud_id=solicitud_id, moderador=moderador)
    _avisar(
        Tipo.SOLICITUD_RESUELTA,
        solicitud.solicitante,
        f"solicitud_resuelta:{solicitud.pk}",
        aprobado=aprobar,
        producto=f"{solicitud.nombre} {solicitud.marca}".strip(),
    )
    accion = Accion.APROBAR_SOLICITUD if aprobar else Accion.RECHAZAR_SOLICITUD
    return _registrar(moderador, accion, "solicitud", solicitud_id, motivo)


@transaction.atomic
def decidir_establecimiento(*, moderador, establecimiento_id: int, aprobar: bool, motivo=""):
    _exigir_moderador(moderador)
    if aprobar:
        local = establecimientos.aprobar_establecimiento(
            establecimiento_id=establecimiento_id, moderador=moderador
        )
    else:
        local = establecimientos.rechazar_establecimiento(
            establecimiento_id=establecimiento_id, moderador=moderador
        )
    _avisar(
        Tipo.ESTABLECIMIENTO_RESUELTO,
        local.sugerido_por,
        f"establecimiento_resuelto:{local.pk}",
        aprobado=aprobar,
        establecimiento=local.nombre,
    )
    accion = Accion.APROBAR_ESTABLECIMIENTO if aprobar else Accion.RECHAZAR_ESTABLECIMIENTO
    return _registrar(moderador, accion, "establecimiento", establecimiento_id, motivo)


@transaction.atomic
def suspender_cuenta(*, moderador, usuario_id: int, motivo: str = ""):
    _exigir_moderador(moderador)
    if usuario_id == moderador.pk:
        raise ValidationError("No puedes suspender tu propia cuenta.")
    try:
        cuentas.suspender_cuenta(usuario_id=usuario_id)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    return _registrar(moderador, Accion.SUSPENDER_CUENTA, "usuario", usuario_id, motivo)
