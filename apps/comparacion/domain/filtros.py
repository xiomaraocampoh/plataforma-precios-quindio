"""Filtros de la comparación por ubicación (RF-19). Python puro — TDD.

Regla de neutralidad (EC-06): un filtro solo REDUCE los resultados; nunca agrega ni reordena.
El orden lo decide únicamente `ranking.ordenar_neutral`.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

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
