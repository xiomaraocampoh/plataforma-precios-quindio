"""Reintentos del envío: máximo 3 intentos con espera creciente (1, 4 y 16 minutos)."""

from datetime import datetime, timedelta

MAX_INTENTOS = 3
ESPERA_BASE = timedelta(minutes=1)


def espera_tras(intentos: int) -> timedelta:
    return ESPERA_BASE * 4 ** max(intentos - 1, 0)


def puede_reintentar(*, intentos: int, ultimo_intento: datetime | None, ahora: datetime) -> bool:
    if intentos >= MAX_INTENTOS:
        return False
    return ultimo_intento is None or ahora >= ultimo_intento + espera_tras(intentos)
