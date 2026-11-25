"""Casos de uso del módulo comercial (escritura). Argumentos solo por nombre.

- RF-C01 crear perfil · RF-C02 verificar (moderador, ADR-015) · RF-C03 precio oficial (30 días)
- RF-C04 promociones (ADR-014) · RF-C06 corrección · RF-C07 confirmar vigencia con un toque

Cada escritura que cambia lo que muestra la comparación invalida su caché por producto al
confirmarse la transacción (ADR-0002). Ninguna escribe en tablas del núcleo, salvo el rol del
usuario, que se asigna con `cuentas.services.asegurar_comercio`.
"""

import secrets
from datetime import date, datetime
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.catalogo import selectors as catalogo
from apps.cuentas import services as cuentas
from apps.establecimientos.models import Establecimiento
from apps.notificaciones.domain.catalogo import Tipo
from apps.notificaciones.services import encolar
from apps.precios.models import ReportePrecio
from core.cache import invalidar_comparacion
from core.limites import permitir

from . import selectors
from .domain.promociones import MotivoPromocion, PromocionInvalidaError, exigir_datos_del_motivo
from .models import PerfilComercio, PrecioOficial, Promocion, SolicitudCorreccion
from .permisos import es_moderador

ROLES_QUE_PUEDEN_SER_COMERCIO = frozenset({"reportante", "comercio"})
ALFABETO_CODIGO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sin 0/O ni 1/I: se dicta sin confusión
LARGO_CODIGO = 6


class ComercioNoVerificadoError(PermissionDenied):
    """Solo un comercio verificado publica (ADR-015)."""


class LimiteComercioError(PermissionDenied):
    """Demasiadas escrituras en una hora (M-16)."""


def _enlace_portal() -> str:
    return f"{settings.SITIO_URL}/comercios/"


def _invalidar(producto_ids) -> None:
    ids = sorted(set(producto_ids))
    transaction.on_commit(lambda: [invalidar_comparacion(pid) for pid in ids])


def _limitar(usuario) -> None:
    maximo = settings.COMERCIOS["ESCRITURAS_POR_HORA"]
    if not permitir("comercios", f"u{usuario.pk}", maximo=maximo, ventana_s=3600):
        raise LimiteComercioError(f"Alcanzaste el límite de {maximo} cambios por hora.")


def _perfil_verificado(usuario) -> PerfilComercio:
    perfil = selectors.perfil_de(usuario)
    if perfil is None or not perfil.verificado:
        raise ComercioNoVerificadoError("Tu comercio aún no está verificado por moderación.")
    _limitar(usuario)
    return perfil


def _exigir_moderador(usuario) -> None:
    if not es_moderador(usuario):
        raise PermissionDenied("Solo moderación puede decidir sobre un comercio.")


def _codigo() -> str:
    return "".join(secrets.choice(ALFABETO_CODIGO) for _ in range(LARGO_CODIGO))


# ---------- RF-C01 y RF-C02 ----------


@transaction.atomic
def crear_perfil(
    *, usuario, establecimiento_id: int, nombre_contacto: str, evidencia: str, telefono: str = ""
) -> PerfilComercio:
    if getattr(usuario, "rol", "") not in ROLES_QUE_PUEDEN_SER_COMERCIO or usuario.is_staff:
        raise ValidationError("Una cuenta de moderación o administración no puede ser un comercio.")
    if selectors.perfil_de(usuario) is not None:
        raise ValidationError("Ya tienes un perfil de comercio.")
    local = Establecimiento.objects.filter(
        pk=establecimiento_id, activo=True, estado=Establecimiento.Estado.APROBADO
    ).first()
    if local is None:
        raise ValidationError("Elige un establecimiento del directorio.")
    if selectors.establecimiento_tiene_perfil(local.pk):
        raise ValidationError("Ese establecimiento ya tiene un perfil de comercio.")
    _limitar(usuario)
    try:
        with transaction.atomic():
            return PerfilComercio.objects.create(
                usuario=usuario,
                establecimiento=local,
                nombre_contacto=nombre_contacto.strip(),
                telefono=telefono.strip(),
                evidencia=evidencia.strip(),
                codigo_verificacion=_codigo(),
            )
    except IntegrityError as exc:  # dos solicitudes a la vez: decide la restricción de la BD
        raise ValidationError("Ese establecimiento ya tiene un perfil de comercio.") from exc


@transaction.atomic
def verificar_perfil(
    *, moderador, perfil_id: int, aprobar: bool, motivo: str = ""
) -> PerfilComercio:
    """ADR-015: un moderador confirma (o no) que la persona representa al comercio."""
    _exigir_moderador(moderador)
    perfil = (
        PerfilComercio.objects.select_for_update()
        .select_related("establecimiento")
        .get(pk=perfil_id)
    )
    if perfil.estado != PerfilComercio.Estado.PENDIENTE:
        raise ValidationError("Este perfil ya fue decidido.")
    if perfil.usuario_id == moderador.pk:
        raise ValidationError("No puedes verificar tu propio comercio.")
    if not aprobar and not motivo.strip():
        raise ValidationError("Indica el motivo para no verificar el perfil.")
    if aprobar:
        cuentas.asegurar_comercio(usuario_id=perfil.usuario_id)
    perfil.estado = PerfilComercio.Estado.VERIFICADO if aprobar else PerfilComercio.Estado.RECHAZADO
    perfil.verificado_por = moderador
    perfil.verificado_en = timezone.now()
    perfil.motivo_decision = motivo.strip()[:300]
    perfil.save(update_fields=["estado", "verificado_por", "verificado_en", "motivo_decision"])
    encolar(
        tipo=Tipo.PERFIL_VERIFICADO,
        clave_idempotencia=f"perfil_verificado:{perfil.pk}",
        usuario=perfil.usuario,
        contexto={
            "nombre": perfil.usuario.username,
            "aprobado": aprobar,
            "establecimiento": perfil.establecimiento.nombre,
            "motivo": perfil.motivo_decision,
            "enlace_portal": _enlace_portal(),
        },
    )
    return perfil


# ---------- RF-C03 y RF-C07 ----------


@transaction.atomic
def publicar_precio_oficial(*, usuario, presentacion_id: int, precio: Decimal) -> PrecioOficial:
    """Publica o actualiza el precio oficial; la vigencia (30 días) corre desde ahora."""
    perfil = _perfil_verificado(usuario)
    if precio is None or precio <= 0:
        raise ValidationError("El precio debe ser mayor que cero.")
    presentacion = catalogo.presentaciones_publicas().filter(pk=presentacion_id).first()
    if presentacion is None:
        raise ValidationError("Elige una presentación del catálogo.")
    oficial, _ = PrecioOficial.objects.update_or_create(
        perfil=perfil,
        presentacion=presentacion,
        defaults={"precio": precio, "confirmado_en": timezone.now()},
    )
    _invalidar([presentacion.producto_id])
    return oficial


@transaction.atomic
def confirmar_vigencia(*, usuario) -> int:
    """RF-C07: con un toque, todos sus precios oficiales siguen vigentes otros 30 días."""
    perfil = _perfil_verificado(usuario)
    precios = perfil.precios.select_related("presentacion")
    productos = [p.presentacion.producto_id for p in precios]
    renovados = precios.update(confirmado_en=timezone.now())
    _invalidar(productos)
    return renovados


@transaction.atomic
def retirar_precio_oficial(*, usuario, precio_id: int) -> None:
    perfil = _perfil_verificado(usuario)
    oficial = perfil.precios.select_related("presentacion").filter(pk=precio_id).first()
    if oficial is None:
        raise ValidationError("Ese precio no es de tu comercio.")
    if perfil.promociones.filter(presentacion_id=oficial.presentacion_id, activa=True).exists():
        raise ValidationError("Termina primero las promociones de esa presentación.")
    producto = oficial.presentacion.producto_id
    oficial.delete()
    _invalidar([producto])


# ---------- RF-C04 ----------


@transaction.atomic
def crear_promocion(
    *,
    usuario,
    presentacion_id: int,
    tipo: str,
    inicio: datetime,
    fin: datetime,
    motivo: str,
    condiciones: str,
    porcentaje: Decimal | None = None,
    precio_especial: Decimal | None = None,
    pague: int | None = None,
    lleve: int | None = None,
    fecha_vencimiento_producto: date | None = None,
) -> Promocion:
    """La promoción se calcula sobre su precio oficial (el regular) y nunca cambia el orden."""
    perfil = _perfil_verificado(usuario)
    oficial = (
        perfil.precios.select_related("presentacion")
        .filter(presentacion_id=presentacion_id)
        .first()
    )
    if oficial is None:
        raise ValidationError("Publica primero el precio oficial de esa presentación.")
    if not condiciones.strip():
        raise ValidationError("Escribe las condiciones de la promoción (Ley 1480 de 2011).")
    promocion = Promocion(
        perfil=perfil,
        presentacion=oficial.presentacion,
        tipo=tipo,
        porcentaje=porcentaje if tipo == Promocion.Tipo.DESCUENTO_PORCENTUAL else None,
        precio_especial=precio_especial if tipo == Promocion.Tipo.PRECIO_ESPECIAL else None,
        pague=pague if tipo == Promocion.Tipo.PAGUE_X_LLEVE_Y else None,
        lleve=lleve if tipo == Promocion.Tipo.PAGUE_X_LLEVE_Y else None,
        inicio=inicio,
        fin=fin,
        motivo=motivo,
        condiciones=condiciones.strip()[:300],
        fecha_vencimiento_producto=fecha_vencimiento_producto,
    )
    try:
        dominio = selectors.promocion_de_dominio(promocion, oficial.precio)
        vencimiento = fecha_vencimiento_producto
        exigir_datos_del_motivo(MotivoPromocion(motivo), vencimiento, dominio.vigencia)
    except (PromocionInvalidaError, ValueError) as exc:
        raise ValidationError(str(exc)) from exc
    promocion.save()
    _invalidar([oficial.presentacion.producto_id])
    return promocion


@transaction.atomic
def finalizar_promocion(*, usuario, promocion_id: int) -> Promocion:
    perfil = _perfil_verificado(usuario)
    promocion = perfil.promociones.select_related("presentacion").filter(pk=promocion_id).first()
    if promocion is None:
        raise ValidationError("Esa promoción no es de tu comercio.")
    promocion.activa = False
    promocion.save(update_fields=["activa"])
    _invalidar([promocion.presentacion.producto_id])
    return promocion


# ---------- RF-C06 ----------


@transaction.atomic
def solicitar_correccion(
    *, usuario, tipo: str, descripcion: str, reporte_id: int | None = None
) -> SolicitudCorreccion:
    perfil = _perfil_verificado(usuario)
    if tipo not in SolicitudCorreccion.Tipo.values:
        raise ValidationError("Elige qué quieres corregir.")
    if not descripcion.strip():
        raise ValidationError("Cuéntanos qué está mal.")
    reporte = None
    if tipo == SolicitudCorreccion.Tipo.PRECIO_REPORTADO:
        reporte = ReportePrecio.objects.filter(
            pk=reporte_id, establecimiento_id=perfil.establecimiento_id
        ).first()
        if reporte is None:
            raise ValidationError("Elige un precio reportado en tu establecimiento.")
    return SolicitudCorreccion.objects.create(
        perfil=perfil, tipo=tipo, reporte=reporte, descripcion=descripcion.strip()[:500]
    )


@transaction.atomic
def resolver_correccion(
    *, moderador, solicitud_id: int, aceptar: bool, respuesta: str = ""
) -> SolicitudCorreccion:
    _exigir_moderador(moderador)
    solicitud = (
        SolicitudCorreccion.objects.select_for_update()
        .select_related("perfil__usuario", "perfil__establecimiento")
        .get(pk=solicitud_id)
    )
    if solicitud.estado != SolicitudCorreccion.Estado.PENDIENTE:
        raise ValidationError("Esta solicitud ya fue resuelta.")
    solicitud.estado = (
        SolicitudCorreccion.Estado.RESUELTA if aceptar else SolicitudCorreccion.Estado.RECHAZADA
    )
    solicitud.respuesta = respuesta.strip()[:500]
    solicitud.resuelta_por = moderador
    solicitud.resuelta_en = timezone.now()
    solicitud.save(update_fields=["estado", "respuesta", "resuelta_por", "resuelta_en"])
    encolar(
        tipo=Tipo.CORRECCION_RESUELTA,
        clave_idempotencia=f"correccion_resuelta:{solicitud.pk}",
        usuario=solicitud.perfil.usuario,
        contexto={
            "nombre": solicitud.perfil.usuario.username,
            "aprobado": aceptar,
            "establecimiento": solicitud.perfil.establecimiento.nombre,
            "respuesta": solicitud.respuesta,
            "enlace_portal": _enlace_portal(),
        },
    )
    return solicitud
