"""Datos de prueba de data/demo/: cargar, refrescar y limpiar. Capa de aplicación.

`cargar` y `refrescar` usan la MISMA lógica que las migraciones de siembra (ADR-0023): los módulos
`apps/<app>/semilla.py`, llamados aquí con el registro real de modelos. Esos módulos replican con
el dominio puro las reglas que aplican los servicios (normalización y duplicados D-05, anomalías
EC-03, una denuncia por persona RF-20, «Sigue igual» idempotente RF-14), porque una migración no
puede usar servicios ni modelos actuales.

Idempotente: cada fila tiene una clave natural, y cada fila de precios.csv un id fijo («P0001»)
que se convierte en un UUID determinista (`id_cliente`); cargar dos veces no duplica nada.
`limpiar` sí pasa por los servicios de cada módulo (borrar respeta lo que usan los datos reales).
"""

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from django.apps import apps as registro
from django.db import transaction
from django.utils import timezone

from apps.catalogo import semilla as semilla_catalogo
from apps.catalogo import services as catalogo
from apps.catalogo.domain.duplicados import normalizar_nombre
from apps.catalogo.models import Categoria, Marca, Producto
from apps.cuentas import services as cuentas
from apps.establecimientos import semilla as semilla_establecimientos
from apps.establecimientos import services as establecimientos
from apps.establecimientos.models import Establecimiento
from apps.precios import semilla as semilla_precios
from apps.precios import services as precios
from apps.precios.models import ReportePrecio
from core.cache import invalidar_comparacion
from core.errores import EnUsoError
from core.semilla import (
    MARCADOR_PRUEBA,
    DatosDePruebaInvalidosError,
    Resumen,
    directorio_por_defecto,
    filas,
)

MARCADOR_SOLICITUD = MARCADOR_PRUEBA  # nombre anterior; lo usan limpiar y las pruebas

# Los comandos capturan DatosDePruebaInvalidosError desde aquí (no importan core directamente)
__all__ = ["DatosDePruebaInvalidosError", "Resumen", "cargar", "limpiar", "refrescar"]


def _invalidar_productos_demo() -> None:
    """La comparación cacheada (ADR-0004) se recalcula tras confirmar la transacción."""
    ids = set(
        ReportePrecio.objects.filter(es_demo=True).values_list(
            "presentacion__producto_id", flat=True
        )
    )

    def invalidar():
        for producto_id in ids:
            invalidar_comparacion(producto_id)

    transaction.on_commit(invalidar)


@transaction.atomic
def cargar(
    *,
    directorio: Path | None = None,
    solo_catalogo: bool = False,
    ahora: datetime | None = None,
) -> Resumen:
    """Carga todo en una transacción: si una fila es inválida no queda nada a medias."""
    directorio = directorio or directorio_por_defecto()
    resumen = Resumen()
    semilla_catalogo.sembrar(registro, directorio=directorio, resumen=resumen)
    semilla_establecimientos.sembrar(registro, directorio=directorio, resumen=resumen)
    if solo_catalogo:
        return resumen
    cuentas.cuentas_prueba.asegurar_cuentas_prueba(contrasena=None)  # autores (sin contraseña)
    semilla_precios.sembrar(
        registro,
        directorio=directorio,
        autores=cuentas.cuentas_prueba.usuarios_de_prueba(),
        ahora=ahora or timezone.now(),
        resumen=resumen,
    )
    _invalidar_productos_demo()
    return resumen


@transaction.atomic
def refrescar(*, directorio: Path | None = None, ahora: datetime | None = None) -> dict[str, int]:
    """refrescar_precios_prueba: vuelve a fechar los precios de prueba (es_demo) según su
    antigüedad relativa del CSV, para que nunca queden todos vencidos."""
    movidos = semilla_precios.refrescar(
        registro, directorio=directorio or directorio_por_defecto(), ahora=ahora or timezone.now()
    )
    _invalidar_productos_demo()
    return movidos


def _borrar_si_libre(objetos, eliminar: Callable) -> int:
    borrados = 0
    for objeto in objetos:
        try:
            eliminar(objeto)
        except EnUsoError:  # lo usa un dato real: se conserva
            continue
        borrados += 1
    return borrados


def _nombres(directorio: Path, archivo: str, campo: str) -> set[str]:
    return {fila[campo].strip() for _, fila in filas(directorio, archivo)}


def _productos_del_csv(directorio: Path) -> list[Producto]:
    claves = {
        (normalizar_nombre(f["marca"]), normalizar_nombre(f["nombre"]))
        for _, f in filas(directorio, "productos.csv")
    }
    candidatos = Producto.objects.select_related("marca").filter(
        nombre_normalizado__in={nombre for _, nombre in claves}
    )
    return [
        p
        for p in candidatos
        if (p.marca.nombre_normalizado if p.marca else "", p.nombre_normalizado) in claves
    ]


@transaction.atomic
def limpiar(*, directorio: Path | None = None) -> dict[str, int]:
    """Borra los datos de prueba. Lo que también usan datos reales se conserva."""
    directorio = directorio or directorio_por_defecto()
    borrados = {
        "precios": precios.borrar_reportes_demo(),
        "solicitudes": catalogo.borrar_solicitudes_pendientes(marcador=MARCADOR_SOLICITUD),
    }
    locales = Establecimiento.objects.filter(
        nombre__in=_nombres(directorio, "establecimientos.csv", "nombre")
    )
    borrados["establecimientos"] = _borrar_si_libre(locales, establecimientos.eliminar)
    borrados["productos"] = _borrar_si_libre(_productos_del_csv(directorio), catalogo.eliminar)
    normales = {normalizar_nombre(n) for n in _nombres(directorio, "marcas.csv", "nombre")}
    marcas = Marca.objects.filter(nombre_normalizado__in=normales)
    borrados["marcas"] = _borrar_si_libre(marcas, catalogo.eliminar)
    categorias = Categoria.objects.filter(
        nombre__in=_nombres(directorio, "categorias.csv", "nombre")
    )
    borrados["categorias"] = _borrar_si_libre(categorias, catalogo.eliminar)
    return borrados
