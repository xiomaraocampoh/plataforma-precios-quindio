"""Casos de uso de escritura de Reportantes (capa de aplicación).

Regla: las vistas (HTMX o API) NO tocan el ORM para escribir; llaman a estos servicios.
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.catalogo.models import Presentacion
from apps.establecimientos.models import Establecimiento
from core.cache import invalidar_comparacion

from .domain.confianza import es_anomalo
from .domain.validaciones import FechaObservacionInvalidaError, normalizar_fecha_observacion
from .domain.vigencia import Fuente, ventana_vigencia
from .models import ConfirmacionPrecio, ReportePrecio
from .selectors import politica_vigencia

TOLERANCIA_RELOJ = timedelta(minutes=5)  # relojes de celular desfasados


class LimiteDeRegistrosExcedidoError(Exception):
    """RN-10: el usuario superó el máximo de registros por hora (ADR-006, M-16)."""


def _exigir_cupo(autor, ahora: datetime) -> None:
    limite = settings.PRECIOS["LIMITE_REPORTES_HORA"]
    recientes = ReportePrecio.objects.filter(
        autor=autor, creado_en__gte=ahora - timedelta(hours=1)
    ).count()
    if recientes >= limite:
        raise LimiteDeRegistrosExcedidoError(
            f"Alcanzaste el límite de {limite} registros por hora. Intenta más tarde."
        )


def _precios_recientes(presentacion_id: int, establecimiento_id: int, desde: datetime):
    return list(
        ReportePrecio.objects.filter(
            presentacion_id=presentacion_id,
            establecimiento_id=establecimiento_id,
            estado=ReportePrecio.Estado.PUBLICADO,
            fecha_observacion__gte=desde,
        )
        .order_by("-fecha_observacion")
        .values_list("precio", flat=True)[:50]
    )


@transaction.atomic
def registrar_reporte(
    *,
    autor,
    presentacion_id: int,
    establecimiento_id: int,
    precio: Decimal,
    fecha_observacion: datetime | None = None,
    id_cliente: uuid.UUID | None = None,
    origen: str = ReportePrecio.Origen.MANUAL,
) -> ReportePrecio:
    """Registra un precio observado. Idempotente por `id_cliente` (sincronización offline).

    `origen` dice si se escribió a mano o se leyó de una etiqueta (ADR-0026); un valor desconocido
    cuenta como manual. No cambia ninguna regla: mismo cupo, anomalías e invalidación."""
    if origen not in ReportePrecio.Origen.values:
        origen = ReportePrecio.Origen.MANUAL
    if id_cliente is not None:
        existente = ReportePrecio.objects.filter(id_cliente=id_cliente).first()
        if existente is not None:
            return existente

    presentacion = (
        Presentacion.objects.select_related("producto__categoria")
        .only("id", "producto_id", "producto__categoria__perecedera")
        .filter(pk=presentacion_id)
        .first()
    )
    if presentacion is None:
        raise ValidationError({"presentacion": "La presentación no existe."})
    if not Establecimiento.objects.filter(pk=establecimiento_id, activo=True).exists():
        raise ValidationError({"establecimiento": "El establecimiento no existe o está inactivo."})

    ahora = timezone.now()
    _exigir_cupo(autor, ahora)  # RN-10: después de la idempotencia, un reenvío no consume cupo
    ventana = ventana_vigencia(
        Fuente.REPORTANTE,
        perecedero=presentacion.producto.categoria.perecedera,
        politica=politica_vigencia(),
    )
    try:  # RN-08
        fecha = normalizar_fecha_observacion(
            fecha_observacion or ahora, ahora, ventana=ventana, tolerancia_reloj=TOLERANCIA_RELOJ
        )
    except FechaObservacionInvalidaError as exc:
        raise ValidationError({"fecha_observacion": str(exc)}) from exc

    recientes = _precios_recientes(
        presentacion_id,
        establecimiento_id,
        desde=ahora - timedelta(days=settings.PRECIOS["VIGENCIA_REPORTE_DIAS"]),
    )
    tolerancia = Decimal(settings.PRECIOS["TOLERANCIA_ANOMALIA"])
    estado = (
        ReportePrecio.Estado.EN_REVISION
        if es_anomalo(precio, recientes, tolerancia)
        else ReportePrecio.Estado.PUBLICADO
    )

    reporte = ReportePrecio.objects.create(
        autor=autor,
        presentacion_id=presentacion_id,
        establecimiento_id=establecimiento_id,
        precio=precio,
        fecha_observacion=fecha,
        estado=estado,
        id_cliente=id_cliente,
        origen=origen,
    )
    producto_id = presentacion.producto_id
    transaction.on_commit(lambda: invalidar_comparacion(producto_id))
    return reporte


@transaction.atomic
def cargar_reporte_historico(
    *,
    autor,
    presentacion_id: int,
    establecimiento_id: int,
    precio: Decimal,
    fecha_observacion: datetime,
    fuente: Fuente = Fuente.REPORTANTE,
    es_demo: bool = False,
    id_cliente: uuid.UUID | None = None,
    revisar_anomalia: bool = False,
) -> ReportePrecio:
    """Crea un reporte con una fecha pasada arbitraria, sin RN-08 ni RN-10.

    Solo para datos de demostración (`cargar_demo`) y pruebas de vigencia: los registros de
    usuarios pasan siempre por `registrar_reporte`. Es una carga histórica: el registro queda
    fechado cuando se observó el precio (`creado_en`), de modo que no consume el cupo por hora
    de nadie (RN-10).

    Con `id_cliente` es idempotente (cargar_datos_prueba usa un UUID fijo por fila del CSV). Con
    `revisar_anomalia` aplica la misma regla de EC-03 que `registrar_reporte`: lejos de la mediana
    reciente, queda «en revisión».
    """
    if id_cliente is not None:
        existente = ReportePrecio.objects.filter(id_cliente=id_cliente).first()
        if existente is not None:
            return existente
    estado = ReportePrecio.Estado.PUBLICADO
    if revisar_anomalia:
        recientes = _precios_recientes(
            presentacion_id,
            establecimiento_id,
            desde=fecha_observacion - timedelta(days=settings.PRECIOS["VIGENCIA_REPORTE_DIAS"]),
        )
        if es_anomalo(precio, recientes, Decimal(settings.PRECIOS["TOLERANCIA_ANOMALIA"])):
            estado = ReportePrecio.Estado.EN_REVISION
    reporte = ReportePrecio.objects.create(
        autor=autor,
        presentacion_id=presentacion_id,
        establecimiento_id=establecimiento_id,
        precio=precio,
        fecha_observacion=fecha_observacion,
        fuente=fuente.value,
        estado=estado,
        es_demo=es_demo,
        id_cliente=id_cliente,
    )
    # `creado_en` es auto_now_add: se fecha después de crear para que sea histórico
    ReportePrecio.objects.filter(pk=reporte.pk).update(creado_en=fecha_observacion)
    reporte.creado_en = fecha_observacion
    producto_id = reporte.presentacion.producto_id
    transaction.on_commit(lambda: invalidar_comparacion(producto_id))
    return reporte


class LimiteDeConfirmacionesExcedidoError(Exception):
    """RN-10 aplicado a «Sigue igual»: máximo de confirmaciones por hora por usuario."""


def confirmar_precio(*, usuario, reporte_id: int) -> tuple[ConfirmacionPrecio, bool]:
    """RF-14: idempotente por usuario, reporte y día; devuelve (confirmación, creada)."""
    reporte = (
        ReportePrecio.objects.select_related("presentacion")
        .filter(pk=reporte_id, estado=ReportePrecio.Estado.PUBLICADO)
        .first()
    )
    if reporte is None:
        raise ValidationError("El precio no existe o no está publicado.")
    if reporte.autor_id == usuario.pk:
        raise ValidationError("No puedes confirmar un precio que reportaste tú.")
    hoy = timezone.localdate()
    existente = ConfirmacionPrecio.objects.filter(
        reporte=reporte, usuario=usuario, fecha=hoy
    ).first()
    if existente is not None:
        return existente, False  # reenvío del mismo día: no consume cupo
    ahora = timezone.now()
    limite = settings.PRECIOS["LIMITE_REPORTES_HORA"]
    recientes = ConfirmacionPrecio.objects.filter(
        usuario=usuario, creado_en__gte=ahora - timedelta(hours=1)
    ).count()
    if recientes >= limite:
        raise LimiteDeConfirmacionesExcedidoError(
            f"Alcanzaste el límite de {limite} confirmaciones por hora. Intenta más tarde."
        )
    try:
        with transaction.atomic():
            confirmacion = ConfirmacionPrecio.objects.create(
                reporte=reporte, usuario=usuario, fecha=hoy
            )
    except IntegrityError:  # doble clic simultáneo: la otra petición ya la creó
        return ConfirmacionPrecio.objects.get(reporte=reporte, usuario=usuario, fecha=hoy), False
    producto_id = reporte.presentacion.producto_id
    transaction.on_commit(lambda: invalidar_comparacion(producto_id))
    return confirmacion, True


@transaction.atomic
def resolver_revision(*, reporte_id: int, aprobar: bool) -> ReportePrecio:
    """RF-21: un reporte «en revisión» se publica o se rechaza. Invalida la comparación."""
    reporte = (
        ReportePrecio.objects.select_for_update().select_related("presentacion").get(pk=reporte_id)
    )
    if reporte.estado != ReportePrecio.Estado.EN_REVISION:
        raise ValidationError("El reporte no está en revisión.")
    reporte.estado = ReportePrecio.Estado.PUBLICADO if aprobar else ReportePrecio.Estado.RECHAZADO
    reporte.save(update_fields=["estado"])
    producto_id = reporte.presentacion.producto_id
    transaction.on_commit(lambda: invalidar_comparacion(producto_id))
    return reporte


@transaction.atomic
def retirar_reporte(*, reporte_id: int) -> ReportePrecio:
    """RF-20: una denuncia aceptada saca el precio de la comparación (queda «rechazado»)."""
    reporte = (
        ReportePrecio.objects.select_for_update().select_related("presentacion").get(pk=reporte_id)
    )
    reporte.estado = ReportePrecio.Estado.RECHAZADO
    reporte.save(update_fields=["estado"])
    producto_id = reporte.presentacion.producto_id
    transaction.on_commit(lambda: invalidar_comparacion(producto_id))
    return reporte


@transaction.atomic
def borrar_reportes_demo() -> int:
    """Borra los reportes de prueba (es_demo) con sus confirmaciones y denuncias (cascada)."""
    demo = ReportePrecio.objects.filter(es_demo=True)
    productos = set(demo.values_list("presentacion__producto_id", flat=True))
    total, _ = demo.delete()
    for producto_id in productos:
        transaction.on_commit(lambda pid=producto_id: invalidar_comparacion(pid))
    return total
