"""Casos de uso de escritura del catálogo (RF-06, D-05)."""

import hashlib
from decimal import Decimal

from django.db import transaction
from django.db.models import ProtectedError, RestrictedError
from django.utils import timezone

from core.cache import invalidar_comparacion
from core.errores import EnUsoError

from . import imagenes
from .domain.duplicados import normalizar_nombre, son_posibles_duplicados
from .models import Categoria, FotoProducto, Marca, Presentacion, Producto, SolicitudCatalogo


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


def marca_por_nombre(nombre: str) -> Marca | None:
    """La marca con ese nombre (sin tildes ni mayúsculas); si no existe la crea. Vacío = None."""
    normal = normalizar_nombre(nombre or "")
    if not normal:
        return None
    marca = Marca.objects.filter(nombre_normalizado=normal).first()
    return marca or Marca.objects.create(nombre=nombre)


def asegurar_categoria(*, nombre: str, perecedera: bool) -> tuple[Categoria, bool]:
    """Categoría por nombre exacto; si existe se conserva tal cual (no se pisan cambios)."""
    return Categoria.objects.get_or_create(nombre=nombre, defaults={"perecedera": perecedera})


class PosibleDuplicadoError(ValueError):
    """D-05: ya hay un producto de la misma marca con un nombre casi igual."""


def asegurar_producto(
    *, nombre: str, marca: Marca | None, categoria: Categoria
) -> tuple[Producto, bool]:
    """Producto por nombre normalizado y marca (D-05). Si solo hay uno PARECIDO de la misma
    marca, no se crea otro: la decisión es humana (PosibleDuplicadoError)."""
    normal = normalizar_nombre(nombre)
    existente = Producto.objects.filter(nombre_normalizado=normal, marca=marca).first()
    if existente is not None:
        return existente, False
    for otro in Producto.objects.filter(marca=marca).only("id", "nombre"):
        if son_posibles_duplicados(nombre, otro.nombre):
            raise PosibleDuplicadoError(f"«{nombre}» se parece a «{otro.nombre}» ({marca}).")
    return Producto.objects.create(nombre=nombre, marca=marca, categoria=categoria), True


def asegurar_presentacion(
    *, producto: Producto, cantidad: Decimal, unidad: str, codigo_barras: str = ""
) -> tuple[Presentacion, bool]:
    """Presentación única por producto, cantidad y unidad. Completa el código si faltaba."""
    presentacion, creada = Presentacion.objects.get_or_create(
        producto=producto,
        cantidad=cantidad,
        unidad=unidad,
        defaults={"codigo_barras": codigo_barras},
    )
    if not creada and codigo_barras and not presentacion.codigo_barras:
        presentacion.codigo_barras = codigo_barras
        presentacion.save(update_fields=["codigo_barras"])
    if creada:
        transaction.on_commit(lambda: invalidar_comparacion(producto.pk))
    return presentacion, creada


def existe_presentacion(*, nombre: str, marca: str, cantidad: Decimal, unidad: str) -> bool:
    normal_marca = normalizar_nombre(marca or "")
    filtro_marca = (
        {"producto__marca__nombre_normalizado": normal_marca}
        if normal_marca
        else {"producto__marca__isnull": True}
    )
    return Presentacion.objects.filter(
        producto__nombre_normalizado=normalizar_nombre(nombre),
        cantidad=cantidad,
        unidad=unidad,
        **filtro_marca,
    ).exists()


@transaction.atomic
def aprobar_solicitud(*, solicitud_id: int, moderador) -> SolicitudCatalogo:
    """Crea (o reutiliza) el producto y la presentación solicitados. RF-21."""
    solicitud = SolicitudCatalogo.objects.select_for_update().get(pk=solicitud_id)
    producto, _ = Producto.objects.get_or_create(
        nombre_normalizado=normalizar_nombre(solicitud.nombre),
        marca=marca_por_nombre(solicitud.marca),
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


# ---------- Panel de administración (las vistas llegan por apps.administracion.services) ----------


def _invalidar_si_es_producto(objeto) -> None:
    if isinstance(objeto, Producto):
        producto_id = objeto.pk
        transaction.on_commit(lambda: invalidar_comparacion(producto_id))


def _olvidar_foto_en_memoria(producto: Producto) -> None:
    """Que `producto.foto_version` lea la BD otra vez (no la relación que ya traía en memoria)."""
    relacion = Producto._meta.get_field("foto")
    if relacion.is_cached(producto):
        relacion.delete_cached_value(producto)


def preparar_foto(datos: bytes) -> bytes:
    """Valida lo que subió una persona y devuelve la miniatura WebP cuadrada (FotoInvalidaError)."""
    return imagenes.procesar(datos)


@transaction.atomic
def guardar_foto(producto: Producto, miniatura: bytes) -> Producto:
    """Guarda (o reemplaza) la foto del producto. Recibe la miniatura ya preparada.

    La versión es una huella del contenido: la misma foto da la misma URL, una distinta la cambia
    y el navegador no sigue mostrando la anterior.
    """
    FotoProducto.objects.update_or_create(
        producto=producto,
        defaults={
            "contenido": miniatura,
            "tipo_contenido": "image/webp",
            "version": hashlib.sha256(miniatura).hexdigest()[:12],
        },
    )
    _olvidar_foto_en_memoria(producto)
    return producto


@transaction.atomic
def quitar_foto(producto: Producto) -> Producto:
    """Quita la foto del producto (sin foto se muestra el ícono de su categoría)."""
    FotoProducto.objects.filter(producto=producto).delete()
    _olvidar_foto_en_memoria(producto)
    return producto


@transaction.atomic
def guardar_formulario(form, formset=None):
    """Guarda un formulario del catálogo ya validado y, si hay, sus presentaciones."""
    objeto = form.save()
    if isinstance(objeto, Producto):
        if form.cleaned_data.get("foto"):
            guardar_foto(objeto, form.cleaned_data["foto"])
        elif form.cleaned_data.get("quitar_foto"):
            quitar_foto(objeto)
    if formset is not None:
        formset.instance = objeto
        try:
            formset.save()
        except (ProtectedError, RestrictedError) as exc:  # red de seguridad: lo valida el form
            raise EnUsoError("Una presentación que quitaste tiene reportes.") from exc
    _invalidar_si_es_producto(objeto)
    return objeto


def cambiar_estado(objeto, *, activo: bool):
    """Activa o desactiva una marca, categoría, producto o presentación (no borra nada)."""
    campo = "activa" if hasattr(objeto, "activa") else "activo"
    setattr(objeto, campo, activo)
    objeto.save(update_fields=[campo])
    _invalidar_si_es_producto(objeto)
    return objeto


def eliminar(objeto) -> None:
    """Borra solo si nada lo referencia (reportes, productos, solicitudes); si no, EnUsoError."""
    try:
        with transaction.atomic():
            objeto.delete()
    except (ProtectedError, RestrictedError) as exc:
        raise EnUsoError("Tiene reportes u otros registros asociados.") from exc


def borrar_solicitudes_pendientes(*, marcador: str) -> int:
    """Borra las solicitudes PENDIENTES cuyo detalle empieza con `marcador` (datos de prueba)."""
    if not marcador:
        raise ValueError("Se necesita un marcador para no borrar solicitudes reales.")
    total, _ = SolicitudCatalogo.objects.filter(
        estado=SolicitudCatalogo.Estado.PENDIENTE, detalle__startswith=marcador
    ).delete()
    return total
