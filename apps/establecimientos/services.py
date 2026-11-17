"""Casos de uso de escritura del directorio (RF-10, RF-21)."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import ProtectedError, RestrictedError
from django.utils import timezone

from core.cache import invalidar_comparacion
from core.errores import EnUsoError

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


def asegurar_establecimiento(
    *, nombre: str, tipo: str, direccion: str, barrio: str, municipio: str
) -> tuple[Establecimiento, bool]:
    """Establecimiento aprobado por nombre y municipio (datos de prueba); no pisa ediciones."""
    if tipo not in Establecimiento.Tipo.values:
        raise ValidationError({"tipo": f"El tipo «{tipo}» no existe."})
    return Establecimiento.objects.get_or_create(
        nombre=nombre,
        municipio=municipio,
        defaults={"tipo": tipo, "direccion": direccion, "barrio": barrio},
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


# ---------- Panel de administración (las vistas llegan por apps.administracion.services) ----------


def _invalidar_comparaciones(establecimiento) -> None:
    """Los precios de este local cambian de visibilidad: se invalida cada producto afectado."""
    productos = list(
        establecimiento.reportes.values_list("presentacion__producto_id", flat=True).distinct()
    )
    transaction.on_commit(lambda: [invalidar_comparacion(p) for p in productos])


@transaction.atomic
def guardar_formulario(form) -> Establecimiento:
    """Alta o edición desde el panel: queda aprobado (lo crea alguien con permiso)."""
    establecimiento = form.save()
    _invalidar_comparaciones(establecimiento)
    return establecimiento


@transaction.atomic
def cambiar_estado(establecimiento: Establecimiento, *, activo: bool) -> Establecimiento:
    if activo and establecimiento.estado == Establecimiento.Estado.PENDIENTE:
        raise ValidationError(
            "Este establecimiento es una sugerencia pendiente: apruébalo en moderación."
        )
    establecimiento.activo = activo
    establecimiento.save(update_fields=["activo", "actualizado_en"])
    _invalidar_comparaciones(establecimiento)
    return establecimiento


def eliminar(establecimiento: Establecimiento) -> None:
    try:
        with transaction.atomic():
            establecimiento.delete()
    except (ProtectedError, RestrictedError) as exc:
        raise EnUsoError("Tiene reportes de precios asociados.") from exc
