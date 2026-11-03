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
from .models import ReportePrecio

TOLERANCIA_RELOJ = timedelta(minutes=5)  # relojes de celular desfasados


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

    ahora = timezone.now()
    fecha = fecha_observacion or ahora
    if fecha > ahora + TOLERANCIA_RELOJ:
        raise ValidationError({"fecha_observacion": "La fecha no puede estar en el futuro."})

    presentacion = Presentacion.objects.only("id", "producto_id").filter(pk=presentacion_id).first()
    if presentacion is None:
        raise ValidationError({"presentacion": "La presentación no existe."})
    if not Establecimiento.objects.filter(pk=establecimiento_id, activo=True).exists():
        raise ValidationError({"establecimiento": "El establecimiento no existe o está inactivo."})

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
