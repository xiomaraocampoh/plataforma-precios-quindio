"""Casos de uso de escritura de Reportantes (capa de aplicación).

Regla: las vistas (HTMX o API) NO tocan el ORM para escribir; llaman a estos servicios.
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.catalogo.models import Presentacion
from apps.establecimientos.models import Establecimiento
from core.cache import invalidar_comparacion

from .domain.confianza import es_anomalo
from .domain.validaciones import FechaObservacionInvalidaError, normalizar_fecha_observacion
from .domain.vigencia import Fuente, ventana_vigencia
from .models import ReportePrecio
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
) -> ReportePrecio:
    """Registra un precio observado. Idempotente por `id_cliente` (sincronización offline)."""
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
) -> ReportePrecio:
    """Crea un reporte con una fecha pasada arbitraria, sin RN-08 ni RN-10.

    Solo para datos de demostración (`cargar_demo --con-vencidos`) y pruebas de vigencia: los
    registros de usuarios pasan siempre por `registrar_reporte`.
    """
    reporte = ReportePrecio.objects.create(
        autor=autor,
        presentacion_id=presentacion_id,
        establecimiento_id=establecimiento_id,
        precio=precio,
        fecha_observacion=fecha_observacion,
        fuente=fuente.value,
    )
    producto_id = reporte.presentacion.producto_id
    transaction.on_commit(lambda: invalidar_comparacion(producto_id))
    return reporte
