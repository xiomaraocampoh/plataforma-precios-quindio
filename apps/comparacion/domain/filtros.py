"""Filtros de la comparación por ubicación (RF-19) y por rango de precio. Python puro — TDD.

Regla de neutralidad (EC-06): un filtro solo REDUCE los resultados; nunca agrega ni reordena.
El orden lo decide únicamente `ranking.ordenar_neutral`.
"""

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from decimal import Decimal

from apps.catalogo.domain.duplicados import normalizar_nombre


@dataclass(frozen=True)
class FiltroUbicacion:
    municipio: str = ""
    barrio: str = ""

    @property
    def activo(self) -> bool:
        return bool(normalizar_nombre(self.municipio) or normalizar_nombre(self.barrio))

    def admite(self, municipio: str, barrio: str) -> bool:
        return _coincide(self.municipio, municipio) and _coincide(self.barrio, barrio)


def _coincide(buscado: str, valor: str) -> bool:
    """Un criterio vacío admite cualquier valor; si no, compara las formas normalizadas."""
    criterio = normalizar_nombre(buscado)
    return not criterio or criterio == normalizar_nombre(valor)


def filtrar[T](
    items: Sequence[T], filtro: FiltroUbicacion, ubicacion: Callable[[T], tuple[str, str]]
) -> list[T]:
    return [item for item in items if filtro.admite(*ubicacion(item))]


@dataclass(frozen=True)
class FiltroPrecio:
    """Rango de precio total, con mínimo y máximo inclusivos. Cualquiera puede faltar."""

    minimo: Decimal | None = None
    maximo: Decimal | None = None

    def __post_init__(self) -> None:
        if (self.minimo is not None and self.minimo < 0) or (
            self.maximo is not None and self.maximo < 0
        ):
            raise ValueError("Los montos no pueden ser negativos.")
        if self.minimo is not None and self.maximo is not None and self.minimo > self.maximo:
            raise ValueError("El precio mínimo no puede ser mayor que el máximo.")

    @property
    def activo(self) -> bool:
        return self.minimo is not None or self.maximo is not None

    def admite(self, precio: Decimal) -> bool:
        return (self.minimo is None or precio >= self.minimo) and (
            self.maximo is None or precio <= self.maximo
        )


def filtrar_por_precio[T](
    items: Sequence[T], filtro: FiltroPrecio, precio: Callable[[T], Decimal]
) -> list[T]:
    return [item for item in items if filtro.admite(precio(item))]


_MILES = re.compile(r"^\d{1,3}(\.\d{3})+$")  # 2.500 · 1.234.567
_PLANO = re.compile(r"^\d+(\.\d+)?$")  # 2500 · 2500.50


def interpretar_monto(texto: str) -> Decimal | None:
    """Convierte lo que escribe una persona en un monto; vacío significa «sin límite».

    Formato colombiano: el punto agrupa miles y la coma separa los decimales.
    """
    limpio = texto.replace("$", "").strip()
    if not limpio:
        return None
    if "," in limpio:
        limpio = limpio.replace(".", "").replace(",", ".")
    elif _MILES.match(limpio):
        limpio = limpio.replace(".", "")
    if not _PLANO.match(limpio):
        raise ValueError(f"No se entiende el monto: {texto!r}.")
    return Decimal(limpio)
