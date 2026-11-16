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
        for buscado, valor in ((self.municipio, municipio), (self.barrio, barrio)):
            buscado = normalizar_nombre(buscado)
            if buscado and buscado != normalizar_nombre(valor):
                return False
        return True


def filtrar[T](
    items: Sequence[T], filtro: FiltroUbicacion, ubicacion: Callable[[T], tuple[str, str]]
) -> list[T]:
    return [item for item in items if filtro.admite(*ubicacion(item))]
