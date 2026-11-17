"""Piezas comunes de la siembra de datos de prueba (ADR-0023).

La siembra la hacen las migraciones de datos (`migrate`) y los comandos `cargar_datos_prueba` y
`crear_cuentas_prueba`. Los dos caminos llaman a los mismos módulos `apps/<app>/semilla.py`, que
reciben el registro de modelos (`apps`): el histórico en una migración, `django.apps.apps` en un
comando. Por eso esos módulos NUNCA importan modelos ni servicios: usan `apps.get_model` y las
funciones puras de `domain/`.

Aquí solo hay lo que no es de ninguna app: leer los CSV de data/demo/, el resumen de la carga y
la regla de cuándo una migración puede sembrar (nunca en producción salvo que se pida).
"""

import csv
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from django.conf import settings

# Marca el texto de las denuncias y solicitudes de prueba: así se reconocen al limpiar o revertir
MARCADOR_PRUEBA = "[Datos de prueba]"


ETIQUETAS = {
    "categorias": "categorías",
    "en_revision": "en revisión",
    "sigue_igual": "«Sigue igual»",
    "sugeridos": "locales sugeridos",
}


class DatosDePruebaInvalidosError(ValueError):
    """Una fila de los CSV no se puede cargar; el mensaje dice archivo, línea y motivo."""


@dataclass
class Resumen:
    nuevos: dict[str, int] = field(default_factory=dict)
    totales: dict[str, int] = field(default_factory=dict)
    avisos: list[str] = field(default_factory=list)

    def sumar(self, clave: str, creado: bool) -> None:
        self.totales[clave] = self.totales.get(clave, 0) + 1
        self.nuevos[clave] = self.nuevos.get(clave, 0) + int(creado)

    def texto(self) -> str:
        """«67 marcas (nuevos: 67), …»: para el aviso de la migración."""
        return ", ".join(
            f"{n} {ETIQUETAS.get(clave, clave)} (nuevos: {self.nuevos[clave]})"
            for clave, n in self.totales.items()
        )


def directorio_por_defecto() -> Path:
    return Path(settings.BASE_DIR) / "data" / "demo"


def filas(directorio: Path, archivo: str) -> list[tuple[str, dict]]:
    """[(«archivo línea N», fila)]. La línea 1 es el encabezado: la primera fila es la línea 2."""
    ruta = directorio / archivo
    if not ruta.exists():
        raise DatosDePruebaInvalidosError(f"No existe {ruta}.")
    with ruta.open(encoding="utf-8-sig", newline="") as f:
        return [(f"{archivo} línea {n}", fila) for n, fila in enumerate(csv.DictReader(f), 2)]


def validar(donde: str, leer: Callable, *args):
    """Aplica `leer`; si falla, el error nombra el archivo y la línea."""
    try:
        return leer(*args)
    except DatosDePruebaInvalidosError:
        raise
    except (ValueError, KeyError) as exc:  # FilaInvalidaError es un ValueError
        motivo = f"no existe «{exc.args[0]}»" if isinstance(exc, KeyError) else str(exc)
        raise DatosDePruebaInvalidosError(f"{donde}: {motivo}") from exc


# ---------- ¿puede sembrar la migración? ----------


def sembrar_datos_activo() -> bool:
    """Catálogo, directorio y precios de prueba: en local (DEBUG) o si se pide explícitamente."""
    return bool(settings.DEBUG or getattr(settings, "SEMBRAR_DATOS_PRUEBA", False))


def sembrar_cuentas_activo() -> bool:
    """Cuentas de prueba: en local (DEBUG) o con SEMBRAR_CUENTAS_PRUEBA=True. Nunca por defecto
    en producción, donde serían cuentas con rol conocido y contraseña compartida."""
    return bool(settings.DEBUG or getattr(settings, "SEMBRAR_CUENTAS_PRUEBA", False))


def avisar(texto: str) -> None:
    """Salida de las migraciones (no tienen self.stdout). Nunca recibe contraseñas."""
    sys.stdout.write(f"\n    {texto}")  # bajo «Applying …»; migrate cierra la línea con « OK»
