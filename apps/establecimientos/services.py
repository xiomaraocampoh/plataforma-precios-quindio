"""Casos de uso de escritura del directorio (RF-10, RF-21)."""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import Establecimiento


def sugerir_establecimiento(
    *,
    autor,
    nombre: str,
    tipo: str,
    direccion: str,
    barrio: str = "",
    municipio: str = "Armenia",
    latitud: Decimal | None = None,
    longitud: Decimal | None = None,
) -> Establecimiento:
    """RF-10: queda pendiente e inactivo; no se usa en la comparación hasta aprobarse."""
    return Establecimiento.objects.create(
        nombre=nombre.strip(),
        tipo=tipo,
        direccion=direccion.strip(),
        barrio=barrio.strip(),
        municipio=municipio.strip() or "Armenia",
        latitud=latitud,
        longitud=longitud,
        activo=False,
        estado=Establecimiento.Estado.PENDIENTE,
        sugerido_por=autor,
    )


@transaction.atomic
def aprobar_establecimiento(*, establecimiento_id: int, moderador) -> Establecimiento:
    return _revisar(establecimiento_id, moderador, Establecimiento.Estado.APROBADO, activo=True)


@transaction.atomic
def rechazar_establecimiento(*, establecimiento_id: int, moderador) -> Establecimiento:
    return _revisar(establecimiento_id, moderador, Establecimiento.Estado.RECHAZADO, activo=False)


def _revisar(establecimiento_id, moderador, estado, *, activo: bool) -> Establecimiento:
    e = Establecimiento.objects.select_for_update().get(pk=establecimiento_id)
    if e.estado != Establecimiento.Estado.PENDIENTE:
        raise ValueError("El establecimiento ya fue revisado.")
    e.estado = estado
    e.activo = activo
    e.revisado_por = moderador
    e.revisado_en = timezone.now()
    e.save(update_fields=["estado", "activo", "revisado_por", "revisado_en", "actualizado_en"])
    return e
