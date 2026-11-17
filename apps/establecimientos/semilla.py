"""Siembra de prueba del directorio de establecimientos (ADR-0023).

La usan la migración `0004_semilla_directorio` y `cargar_datos_prueba`. Recibe el registro de
modelos (`apps`): no importa modelos ni servicios. Siembra solo los locales aprobados; el
sugerido pendiente necesita un autor y lo siembra `apps/precios/semilla.py` junto con los demás
escenarios de moderación.
"""

from pathlib import Path

from django.db import transaction
from django.db.models import ProtectedError

from apps.administracion.domain.datos_prueba import leer_establecimiento
from core.semilla import Resumen, filas, validar


def _aprobados(directorio: Path):
    for donde, fila in filas(directorio, "establecimientos.csv"):
        if (fila.get("estado") or "aprobado").strip() != "pendiente":
            yield donde, fila


def sembrar(apps, *, directorio: Path, resumen: Resumen) -> None:
    """Local aprobado por nombre y municipio; si ya existe no se pisan sus ediciones."""
    Establecimiento = apps.get_model("establecimientos", "Establecimiento")
    for donde, fila in _aprobados(directorio):
        datos = validar(donde, leer_establecimiento, fila)
        _, creado = Establecimiento.objects.get_or_create(
            nombre=datos.nombre,
            municipio=datos.municipio,
            defaults={"tipo": datos.tipo, "direccion": datos.direccion, "barrio": datos.barrio},
        )
        resumen.sumar("establecimientos", creado)


def revertir(apps, *, directorio: Path) -> int:
    """Borra los locales sembrados que ningún precio usa."""
    Establecimiento = apps.get_model("establecimientos", "Establecimiento")
    borrados = 0
    for donde, fila in _aprobados(directorio):
        datos = validar(donde, leer_establecimiento, fila)
        for local in Establecimiento.objects.filter(nombre=datos.nombre, municipio=datos.municipio):
            try:
                with transaction.atomic():
                    local.delete()
            except ProtectedError:  # lo usa un precio: se conserva
                continue
            borrados += 1
    return borrados
