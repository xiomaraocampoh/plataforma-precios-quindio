"""Validaciones de dominio del registro de precios. Python puro — TDD.

RN-08 (Consolidado, tabla 42; ADR-009): la fecha de observación no puede ser futura ni
anterior al inicio de la ventana de vigencia. Se tolera un pequeño desfase del reloj del
celular; en ese caso la fecha se ajusta al momento actual para que nunca se almacene un
precio "del futuro".
"""

from datetime import datetime, timedelta


class FechaObservacionInvalidaError(ValueError):
    """La fecha de observación está en el futuro o fuera de la ventana de vigencia."""


def normalizar_fecha_observacion(
    fecha: datetime,
    ahora: datetime,
    *,
    ventana: timedelta,
    tolerancia_reloj: timedelta,
) -> datetime:
    if fecha > ahora + tolerancia_reloj:
        raise FechaObservacionInvalidaError("La fecha de observación no puede estar en el futuro.")
    if fecha < ahora - ventana:
        raise FechaObservacionInvalidaError(
            "La fecha de observación es anterior a la ventana de vigencia: ese precio ya venció."
        )
    return min(fecha, ahora)
