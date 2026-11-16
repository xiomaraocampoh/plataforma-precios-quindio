"""Casos de uso de escritura del catálogo (RF-06, D-05)."""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .domain.duplicados import normalizar_nombre
from .models import Presentacion, Producto, SolicitudCatalogo


def solicitar_producto(
    *,
    solicitante,
    nombre: str,
    marca: str,
    categoria_id: int,
    cantidad: Decimal,
    unidad: str,
    codigo_barras: str = "",
    detalle: str = "",
) -> SolicitudCatalogo:
    """Registra la solicitud. Queda pendiente y no entra al catálogo hasta que se apruebe."""
    return SolicitudCatalogo.objects.create(
        solicitante=solicitante,
        nombre=nombre.strip(),
        marca=marca.strip(),
        categoria_id=categoria_id,
        cantidad=cantidad,
        unidad=unidad,
        codigo_barras=codigo_barras.strip(),
        detalle=detalle.strip(),
    )


def existe_presentacion(*, nombre: str, marca: str, cantidad: Decimal, unidad: str) -> bool:
    return Presentacion.objects.filter(
        producto__nombre_normalizado=normalizar_nombre(nombre),
        producto__marca__iexact=marca.strip(),
        cantidad=cantidad,
        unidad=unidad,
    ).exists()


@transaction.atomic
def aprobar_solicitud(*, solicitud_id: int, moderador) -> SolicitudCatalogo:
    """Crea (o reutiliza) el producto y la presentación solicitados. RF-21."""
    solicitud = SolicitudCatalogo.objects.select_for_update().get(pk=solicitud_id)
    producto, _ = Producto.objects.get_or_create(
        nombre_normalizado=normalizar_nombre(solicitud.nombre),
        marca=solicitud.marca,
        defaults={"nombre": solicitud.nombre, "categoria_id": solicitud.categoria_id},
    )
    presentacion, _ = Presentacion.objects.get_or_create(
        producto=producto,
        cantidad=solicitud.cantidad,
        unidad=solicitud.unidad,
        defaults={"codigo_barras": solicitud.codigo_barras},
    )
    return _resolver(solicitud, SolicitudCatalogo.Estado.APROBADA, moderador, presentacion)


@transaction.atomic
def rechazar_solicitud(*, solicitud_id: int, moderador) -> SolicitudCatalogo:
    solicitud = SolicitudCatalogo.objects.select_for_update().get(pk=solicitud_id)
    return _resolver(solicitud, SolicitudCatalogo.Estado.RECHAZADA, moderador, None)


def _resolver(solicitud, estado, moderador, presentacion) -> SolicitudCatalogo:
    if solicitud.estado != SolicitudCatalogo.Estado.PENDIENTE:
        raise ValueError("La solicitud ya fue resuelta.")
    solicitud.estado = estado
    solicitud.resuelto_por = moderador
    solicitud.resuelto_en = timezone.now()
    solicitud.presentacion_creada = presentacion
    solicitud.save(update_fields=["estado", "resuelto_por", "resuelto_en", "presentacion_creada"])
    return solicitud
