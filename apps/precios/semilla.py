"""Siembra de precios de prueba y de sus escenarios de moderación (ADR-0023).

La usan la migración `0004_semilla_precios_prueba`, `cargar_datos_prueba` y
`refrescar_precios_prueba`. Recibe el registro de modelos (`apps`): no importa modelos ni
servicios, así que las reglas que en la aplicación aplican los servicios se replican aquí con las
mismas funciones puras del dominio:

- EC-03: un precio lejos de la mediana reciente (`es_anomalo`) queda «en revisión».
- RF-14: «Sigue igual» solo sobre un precio publicado y de otra persona; una por persona.
- RF-20: una denuncia por persona y precio, sobre un precio publicado y ajeno.
- Las fechas son relativas («hace N días» en precios.csv): se calculan desde `ahora`.

Idempotente: cada fila de precios.csv tiene un id fijo («P0001») que se convierte en un UUID
determinista (`id_cliente`), el mismo que usaba `cargar_datos_prueba` antes de este cambio.
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from apps.administracion.domain.datos_prueba import (
    fecha_de_observacion,
    leer_cantidad,
    leer_establecimiento,
    leer_fuente,
    leer_precio,
    leer_unidad,
)
from apps.catalogo.domain.duplicados import normalizar_nombre
from core.semilla import MARCADOR_PRUEBA, DatosDePruebaInvalidosError, Resumen, filas, validar

from .domain.confianza import es_anomalo

# Espacio de nombres fijo: el UUID de cada fila no cambia entre corridas (idempotencia)
ESPACIO_UUID = uuid.UUID("5b0f5d0e-8e1c-4c47-9a57-6d2f0c0de001")
PUBLICADO, EN_REVISION = "publicado", "en_revision"
MUESTRAS_RECIENTES = 50  # las mismas que mira registrar_reporte


def id_cliente(id_fila: str) -> uuid.UUID:
    return uuid.uuid5(ESPACIO_UUID, id_fila.strip())


def _indice_presentaciones(apps) -> dict[tuple, int]:
    """{(marca, producto, cantidad, unidad): id}, normalizados como en el CSV."""
    Presentacion = apps.get_model("catalogo", "Presentacion")
    indice = {}
    for p in Presentacion.objects.select_related("producto__marca"):
        marca = p.producto.marca.nombre_normalizado if p.producto.marca_id else ""
        indice[(marca, p.producto.nombre_normalizado, p.cantidad, p.unidad)] = p.pk
    return indice


def _locales(apps) -> dict[str, int]:
    Establecimiento = apps.get_model("establecimientos", "Establecimiento")
    aprobados = Establecimiento.objects.filter(estado="aprobado").order_by("pk")
    return {nombre: pk for pk, nombre in aprobados.values_list("pk", "nombre")}


def _leer_precio(fila, presentaciones, locales, autores, ahora) -> dict:
    clave = (
        normalizar_nombre(fila["marca"]),
        normalizar_nombre(fila["producto"]),
        leer_cantidad(fila["cantidad"]),
        leer_unidad(fila["unidad"]),
    )
    return {
        "autor": autores[fila["autor"].strip()],
        "presentacion_id": presentaciones[clave],
        "establecimiento_id": locales[fila["establecimiento"].strip()],
        "precio": leer_precio(fila["precio"]),
        "fecha_observacion": _fecha(ahora, fila),
        "fuente": leer_fuente(fila["fuente_tipo"]),
    }


def _estado(reporte_modelo, datos: dict) -> str:
    """EC-03, la misma regla que registrar_reporte: se compara con lo publicado en la ventana."""
    desde = datos["fecha_observacion"] - timedelta(days=settings.PRECIOS["VIGENCIA_REPORTE_DIAS"])
    recientes = list(
        reporte_modelo.objects.filter(
            presentacion_id=datos["presentacion_id"],
            establecimiento_id=datos["establecimiento_id"],
            estado=PUBLICADO,
            fecha_observacion__gte=desde,
        )
        .order_by("-fecha_observacion")
        .values_list("precio", flat=True)[:MUESTRAS_RECIENTES]
    )
    tolerancia = Decimal(settings.PRECIOS["TOLERANCIA_ANOMALIA"])
    return EN_REVISION if es_anomalo(datos["precio"], recientes, tolerancia) else PUBLICADO


def _precios(apps, directorio, autores, ahora, resumen) -> dict[str, object]:
    """Las filas van en orden: las de base de una anomalía antes que el precio anómalo."""
    ReportePrecio = apps.get_model("precios", "ReportePrecio")
    presentaciones, locales = _indice_presentaciones(apps), _locales(apps)
    leidas = [(d, f, id_cliente(f["id"])) for d, f in filas(directorio, "precios.csv")]
    existentes = ReportePrecio.objects.in_bulk([u for _, _, u in leidas], field_name="id_cliente")
    resultado = {}
    for donde, fila, uid in leidas:
        reporte = existentes.get(uid)
        if reporte is None:
            datos = validar(donde, _leer_precio, fila, presentaciones, locales, autores, ahora)
            reporte = ReportePrecio.objects.create(
                **datos, estado=_estado(ReportePrecio, datos), es_demo=True, id_cliente=uid
            )
            # `creado_en` es auto_now_add: se fecha después para que sea histórico (RN-10)
            ReportePrecio.objects.filter(pk=reporte.pk).update(creado_en=datos["fecha_observacion"])
        resultado[fila["id"].strip()] = reporte
        resumen.sumar("precios", uid not in existentes)
        if reporte.estado == EN_REVISION:
            resumen.sumar("en_revision", uid not in existentes)
    return resultado


def _exigir_ajeno_y_publicado(donde: str, reporte, usuario) -> None:
    if reporte.estado != PUBLICADO:
        raise DatosDePruebaInvalidosError(f"{donde}: el precio no está publicado.")
    if reporte.autor_id == usuario.pk:
        raise DatosDePruebaInvalidosError(f"{donde}: el precio es de la misma persona.")


def _sigue_igual(apps, donde, reporte, usuario, ahora) -> bool:
    ConfirmacionPrecio = apps.get_model("precios", "ConfirmacionPrecio")
    if ConfirmacionPrecio.objects.filter(reporte=reporte, usuario=usuario).exists():
        return False  # idempotente también entre días distintos
    _exigir_ajeno_y_publicado(donde, reporte, usuario)
    confirmacion = ConfirmacionPrecio.objects.create(
        reporte=reporte, usuario=usuario, fecha=timezone.localdate(ahora)
    )
    ConfirmacionPrecio.objects.filter(pk=confirmacion.pk).update(creado_en=ahora)
    return True


def _denuncia(apps, donde, reporte, usuario, fila) -> bool:
    Denuncia = apps.get_model("moderacion", "Denuncia")
    if Denuncia.objects.filter(reporte=reporte, denunciante=usuario).exists():
        return False  # una por persona (una_denuncia_por_usuario)
    _exigir_ajeno_y_publicado(donde, reporte, usuario)
    motivo = fila["motivo"].strip()
    if motivo not in {"precio_falso", "producto", "establecimiento", "otro"}:
        raise DatosDePruebaInvalidosError(f"{donde}: motivo desconocido «{motivo}».")
    Denuncia.objects.create(
        reporte=reporte,
        denunciante=usuario,
        motivo=motivo,
        detalle=f"{MARCADOR_PRUEBA} {fila['detalle'].strip()}",
    )
    return True


def _acciones(apps, directorio, reportes, autores, ahora, resumen) -> None:
    for donde, fila in filas(directorio, "acciones.csv"):
        usuario = validar(donde, lambda f: autores[f["usuario"].strip()], fila)
        reporte = validar(donde, lambda f: reportes[f["precio_id"].strip()], fila)
        accion = fila["accion"].strip()
        if accion == "sigue_igual":
            resumen.sumar("sigue_igual", _sigue_igual(apps, donde, reporte, usuario, ahora))
        elif accion == "denuncia":
            resumen.sumar("denuncias", _denuncia(apps, donde, reporte, usuario, fila))
        else:
            raise DatosDePruebaInvalidosError(f"{donde}: acción desconocida «{accion}».")


def _solicitudes(apps, directorio, autores, resumen) -> None:
    """RF-06: quedan pendientes; una se parece a un producto existente (D-05)."""
    SolicitudCatalogo = apps.get_model("catalogo", "SolicitudCatalogo")
    Categoria = apps.get_model("catalogo", "Categoria")
    for donde, fila in filas(directorio, "solicitudes.csv"):
        solicitante = validar(donde, lambda f: autores[f["solicitante"].strip()], fila)
        nombre, marca = fila["nombre"].strip(), fila["marca"].strip()
        ya = SolicitudCatalogo.objects.filter(
            solicitante=solicitante, nombre=nombre, marca=marca
        ).exists()
        if not ya:
            categoria = Categoria.objects.filter(nombre=fila["categoria"].strip()).first()
            if categoria is None:
                raise DatosDePruebaInvalidosError(f"{donde}: no existe la categoría.")
            SolicitudCatalogo.objects.create(
                solicitante=solicitante,
                nombre=nombre,
                marca=marca,
                categoria=categoria,
                cantidad=validar(donde, leer_cantidad, fila["cantidad"]),
                unidad=validar(donde, leer_unidad, fila["unidad"]),
                codigo_barras=(fila.get("codigo_barras") or "").strip(),
                detalle=f"{MARCADOR_PRUEBA} {(fila.get('detalle') or '').strip()}",
            )
        resumen.sumar("solicitudes", not ya)


def _pendientes(directorio: Path):
    for donde, fila in filas(directorio, "establecimientos.csv"):
        if (fila.get("estado") or "").strip() == "pendiente":
            yield donde, fila


def _sugeridos(apps, directorio, autores, resumen) -> None:
    """RF-10: el local sugerido queda pendiente e inactivo hasta que moderación lo apruebe."""
    Establecimiento = apps.get_model("establecimientos", "Establecimiento")
    for donde, fila in _pendientes(directorio):
        datos = validar(donde, leer_establecimiento, fila)
        ya = Establecimiento.objects.filter(nombre=datos.nombre, municipio=datos.municipio).exists()
        if not ya:
            Establecimiento.objects.create(
                nombre=datos.nombre,
                tipo=datos.tipo,
                direccion=datos.direccion,
                barrio=datos.barrio,
                municipio=datos.municipio,
                activo=False,
                estado="pendiente",
                sugerido_por=validar(donde, lambda f: autores[f["sugerido_por"].strip()], fila),
            )
        resumen.sumar("sugeridos", not ya)


def sembrar(apps, *, directorio: Path, autores: dict, ahora: datetime, resumen: Resumen) -> None:
    """Precios (con es_demo=True) y escenarios: «Sigue igual», denuncias, solicitudes y el local
    sugerido. `autores` son las cuentas de prueba por nombre de usuario."""
    reportes = _precios(apps, directorio, autores, ahora, resumen)
    _acciones(apps, directorio, reportes, autores, ahora, resumen)
    _solicitudes(apps, directorio, autores, resumen)
    _sugeridos(apps, directorio, autores, resumen)


# ---------- mantenimiento ----------


def refrescar(apps, *, directorio: Path, ahora: datetime) -> dict[str, int]:
    """Vuelve a fechar los precios de prueba según su antigüedad relativa del CSV.

    Así el conjunto nunca queda todo vencido: lo que el CSV dice «hace 2 días» vuelve a estar a 2
    días de `ahora`, y los escenarios vencidos (8, 4 y 31 días) siguen justo fuera de su ventana.
    Solo toca reportes con es_demo=True. Devuelve cuántos precios y confirmaciones se movieron.
    """
    ReportePrecio = apps.get_model("precios", "ReportePrecio")
    ConfirmacionPrecio = apps.get_model("precios", "ConfirmacionPrecio")
    fechas = {
        id_cliente(f["id"]): validar(donde, _fecha, ahora, f)
        for donde, f in filas(directorio, "precios.csv")
    }
    reportes = list(ReportePrecio.objects.filter(es_demo=True, id_cliente__in=list(fechas)))
    for reporte in reportes:
        reporte.fecha_observacion = reporte.creado_en = fechas[reporte.id_cliente]
    ReportePrecio.objects.bulk_update(reportes, ["fecha_observacion", "creado_en"], batch_size=200)
    movidas = _refrescar_confirmaciones(ConfirmacionPrecio, directorio, ahora)
    return {"precios": len(reportes), "confirmaciones": movidas}


def _fecha(ahora: datetime, fila: dict) -> datetime:
    return fecha_de_observacion(ahora, dias=fila["dias_atras"], horas=fila["horas_atras"])


def _refrescar_confirmaciones(confirmacion_modelo, directorio: Path, ahora: datetime) -> int:
    """Los «Sigue igual» de acciones.csv pasan a hoy, como cuando se sembraron."""
    hoy = timezone.localdate(ahora)
    movidas = 0
    for _, fila in filas(directorio, "acciones.csv"):
        if fila["accion"].strip() != "sigue_igual":
            continue
        actual = confirmacion_modelo.objects.filter(
            reporte__id_cliente=id_cliente(fila["precio_id"]),
            reporte__es_demo=True,
            usuario__username=fila["usuario"].strip(),
        )
        ultima = actual.order_by("-creado_en").first()
        if ultima is None or actual.filter(fecha=hoy).exclude(pk=ultima.pk).exists():
            continue  # no existe, o ya hay otra de hoy (una por día)
        actual.filter(pk=ultima.pk).update(fecha=hoy, creado_en=ahora)
        movidas += 1
    return movidas


# ---------- reversa ----------


def revertir(apps, *, directorio: Path, autores: dict) -> dict[str, int]:
    """Quita solo lo sembrado: los precios por su id_cliente (las confirmaciones y denuncias caen
    en cascada) y las solicitudes y sugerencias de las cuentas de prueba con el marcador."""
    ReportePrecio = apps.get_model("precios", "ReportePrecio")
    SolicitudCatalogo = apps.get_model("catalogo", "SolicitudCatalogo")
    Establecimiento = apps.get_model("establecimientos", "Establecimiento")
    uids = [id_cliente(f["id"]) for _, f in filas(directorio, "precios.csv")]
    sembrados = ReportePrecio.objects.filter(es_demo=True, id_cliente__in=uids)
    precios = sembrados.count()
    sembrados.delete()
    solicitudes, _ = SolicitudCatalogo.objects.filter(
        estado="pendiente",
        solicitante__in=list(autores.values()),
        detalle__startswith=MARCADOR_PRUEBA,
    ).delete()
    nombres = Q(pk__in=[])
    for donde, fila in _pendientes(directorio):
        datos = validar(donde, leer_establecimiento, fila)
        nombres |= Q(nombre=datos.nombre, municipio=datos.municipio)
    sugeridos, _ = (
        Establecimiento.objects.filter(nombres, estado="pendiente", reportes__isnull=True)
        .filter(sugerido_por__in=list(autores.values()))
        .delete()
    )
    return {"precios": precios, "solicitudes": solicitudes, "sugeridos": sugeridos}
