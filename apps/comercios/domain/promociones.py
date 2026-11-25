"""Promociones como estrategias intercambiables (ADR-014, RF-C04). Python puro — TDD.

Cada tipo calcula cuánto cuesta llevar N empaques a partir del precio regular (el precio oficial
del comercio). El orden de la comparación NUNCA usa estos valores (EC-06, `_clave_neutral`): la
promoción es una etiqueta con su precio efectivo y sus condiciones. «Pague X lleve Y» exige llevar
varias unidades, por eso tampoco podría ordenar.

`aplicar_a_cantidad` queda para la canasta (ADR-0029): el costo de N unidades con la promoción.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from typing import Protocol

from apps.catalogo.domain.normalizacion import CENTAVOS, Unidad, precio_por_unidad
from apps.comparacion.domain.tarjeta import formatear_pesos


class PromocionInvalidaError(ValueError):
    """Los datos de la promoción no forman una promoción válida."""


class TipoPromocion(StrEnum):
    DESCUENTO_PORCENTUAL = "descuento_porcentual"
    PRECIO_ESPECIAL = "precio_especial"
    PAGUE_X_LLEVE_Y = "pague_x_lleve_y"


class MotivoPromocion(StrEnum):
    """Origen y motivo (RF-C04): se muestran junto al precio (Ley 1480 de 2011)."""

    TEMPORADA = "temporada"
    LIQUIDACION = "liquidacion"
    PROXIMO_A_VENCER = "proximo_a_vencer"
    LANZAMIENTO = "lanzamiento"
    OTRO = "otro"


def _centavos(valor: Decimal) -> Decimal:
    return valor.quantize(CENTAVOS, rounding=ROUND_HALF_UP)


class Estrategia(Protocol):
    tipo: TipoPromocion

    def costo(self, precio_regular: Decimal, cantidad: int) -> Decimal: ...

    def describir(self) -> str: ...

    def validar_contra(self, precio_regular: Decimal) -> None: ...

    @property
    def unidades_minimas(self) -> int: ...


@dataclass(frozen=True)
class DescuentoPorcentual:
    porcentaje: Decimal
    tipo = TipoPromocion.DESCUENTO_PORCENTUAL

    def __post_init__(self) -> None:
        # 0 % no es promoción; 100 % sería regalar el producto
        if not Decimal("0") < self.porcentaje < Decimal("100"):
            raise PromocionInvalidaError("El descuento debe ser mayor que 0 % y menor que 100 %.")

    @property
    def unidades_minimas(self) -> int:
        return 1

    def costo(self, precio_regular: Decimal, cantidad: int) -> Decimal:
        por_empaque = _centavos(precio_regular * (Decimal("100") - self.porcentaje) / 100)
        return por_empaque * cantidad

    def describir(self) -> str:
        texto = format(self.porcentaje.normalize(), "f").replace(".", ",")
        return f"{texto} % de descuento"

    def validar_contra(self, precio_regular: Decimal) -> None:
        """Cualquier precio regular positivo admite un descuento válido."""


@dataclass(frozen=True)
class PrecioEspecial:
    precio: Decimal
    tipo = TipoPromocion.PRECIO_ESPECIAL

    def __post_init__(self) -> None:
        if self.precio <= 0:
            raise PromocionInvalidaError("El precio especial debe ser positivo.")

    @property
    def unidades_minimas(self) -> int:
        return 1

    def costo(self, precio_regular: Decimal, cantidad: int) -> Decimal:
        return self.precio * cantidad

    def describir(self) -> str:
        return f"Precio especial de {formatear_pesos(self.precio)}"

    def validar_contra(self, precio_regular: Decimal) -> None:
        if self.precio >= precio_regular:
            raise PromocionInvalidaError("El precio especial debe ser menor que el precio regular.")


@dataclass(frozen=True)
class PagueXLleveY:
    pague: int
    lleve: int
    tipo = TipoPromocion.PAGUE_X_LLEVE_Y

    def __post_init__(self) -> None:
        if self.pague < 1 or self.lleve <= self.pague:
            raise PromocionInvalidaError(
                "En «pague X lleve Y» se paga al menos 1 y se lleva más de lo que se paga."
            )

    @property
    def unidades_minimas(self) -> int:
        return self.lleve

    def costo(self, precio_regular: Decimal, cantidad: int) -> Decimal:
        grupos, sueltas = divmod(cantidad, self.lleve)
        return precio_regular * (grupos * self.pague + sueltas)

    def describir(self) -> str:
        return f"Lleve {self.lleve}, pague {self.pague}"

    def validar_contra(self, precio_regular: Decimal) -> None:
        """El ahorro sale del precio regular: no hay nada más que validar."""


@dataclass(frozen=True)
class Vigencia:
    inicio: datetime
    fin: datetime

    def __post_init__(self) -> None:
        if self.fin <= self.inicio:
            raise PromocionInvalidaError("La promoción debe terminar después de empezar.")

    def vigente_en(self, momento: datetime) -> bool:
        return self.inicio <= momento < self.fin


@dataclass(frozen=True)
class Promocion:
    estrategia: Estrategia
    precio_regular: Decimal
    vigencia: Vigencia

    def __post_init__(self) -> None:
        if self.precio_regular <= 0:
            raise PromocionInvalidaError("El precio regular debe ser positivo.")
        self.estrategia.validar_contra(self.precio_regular)

    @property
    def unidades_minimas(self) -> int:
        return self.estrategia.unidades_minimas

    def vigente_en(self, momento: datetime) -> bool:
        return self.vigencia.vigente_en(momento)

    def precio_efectivo(self) -> Decimal:
        """Por empaque, llevando las unidades mínimas de la promoción."""
        n = self.unidades_minimas
        return _centavos(self.estrategia.costo(self.precio_regular, n) / n)


@dataclass(frozen=True)
class CostoCantidad:
    total: Decimal
    regular: Decimal
    aplicada: bool

    @property
    def ahorro(self) -> Decimal:
        return self.regular - self.total


def aplicar_a_cantidad(
    promocion: Promocion, cantidad: int, *, momento: datetime | None = None
) -> CostoCantidad:
    """Costo de llevar `cantidad` empaques. Fuera de la vigencia se cobra el precio regular."""
    if cantidad < 1:
        raise ValueError("La cantidad debe ser al menos 1.")
    regular = promocion.precio_regular * cantidad
    if momento is not None and not promocion.vigente_en(momento):
        return CostoCantidad(total=regular, regular=regular, aplicada=False)
    total = promocion.estrategia.costo(promocion.precio_regular, cantidad)
    return CostoCantidad(total=total, regular=regular, aplicada=True)


def precio_efectivo_por_unidad(
    promocion: Promocion, cantidad: Decimal, unidad: Unidad | str
) -> tuple[Decimal, Unidad]:
    """$/kg, $/L o $/und del precio efectivo; siempre con `precio_por_unidad` (M-05)."""
    return precio_por_unidad(promocion.precio_efectivo(), cantidad, unidad)


def estrategia_de(
    tipo: str,
    *,
    porcentaje: Decimal | None = None,
    precio_especial: Decimal | None = None,
    pague: int | None = None,
    lleve: int | None = None,
) -> Estrategia:
    """La estrategia de un tipo a partir de sus datos (los de un formulario o una fila)."""
    try:
        tipo_valido = TipoPromocion(tipo)
    except ValueError as exc:
        raise PromocionInvalidaError(f"Tipo de promoción desconocido: {tipo}.") from exc
    if tipo_valido == TipoPromocion.DESCUENTO_PORCENTUAL and porcentaje is not None:
        return DescuentoPorcentual(porcentaje)
    if tipo_valido == TipoPromocion.PRECIO_ESPECIAL and precio_especial is not None:
        return PrecioEspecial(precio_especial)
    if tipo_valido == TipoPromocion.PAGUE_X_LLEVE_Y and pague is not None and lleve is not None:
        return PagueXLleveY(pague=pague, lleve=lleve)
    raise PromocionInvalidaError("Faltan los datos de este tipo de promoción.")


def exigir_datos_del_motivo(
    motivo: MotivoPromocion | str, fecha_vencimiento: date | None, vigencia: Vigencia
) -> None:
    """RF-C04: si el motivo es «próximo a vencer», la fecha de vencimiento es obligatoria y la
    promoción no dura más que el producto. Los demás motivos no llevan esa fecha."""
    if MotivoPromocion(motivo) != MotivoPromocion.PROXIMO_A_VENCER:
        if fecha_vencimiento is not None:
            raise PromocionInvalidaError("La fecha de vencimiento solo aplica a «próximo a vencer».")
        return
    if fecha_vencimiento is None:
        raise PromocionInvalidaError("Indica la fecha de vencimiento del producto.")
    if vigencia.fin.date() > fecha_vencimiento:
        raise PromocionInvalidaError("La promoción no puede terminar después del vencimiento.")
