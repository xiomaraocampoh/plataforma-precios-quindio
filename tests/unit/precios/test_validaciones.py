"""RN-08: la fecha de observación no puede ser futura ni anterior a la ventana de vigencia.

Origen: ADR-009 del Consolidado (registro tolerante a conectividad limitada) — el reporte
conserva la fecha de observación, no la de llegada, y el servidor la valida.
"""

from datetime import UTC, datetime, timedelta

import pytest

from apps.precios.domain.validaciones import (
    FechaObservacionInvalidaError,
    normalizar_fecha_observacion,
)

pytestmark = pytest.mark.unit

AHORA = datetime(2026, 11, 15, 12, 0, tzinfo=UTC)
VENTANA = timedelta(days=7)
TOLERANCIA = timedelta(minutes=5)


def _normalizar(fecha):
    return normalizar_fecha_observacion(fecha, AHORA, ventana=VENTANA, tolerancia_reloj=TOLERANCIA)


def test_fecha_pasada_dentro_de_la_ventana_se_conserva():
    fecha = AHORA - timedelta(days=2)
    assert _normalizar(fecha) == fecha


def test_reloj_adelantado_dentro_de_la_tolerancia_se_ajusta_a_ahora():
    assert _normalizar(AHORA + timedelta(minutes=2)) == AHORA


def test_fecha_futura_mas_alla_de_la_tolerancia_es_rechazada():
    with pytest.raises(FechaObservacionInvalidaError):
        _normalizar(AHORA + timedelta(minutes=5, seconds=1))


def test_fecha_en_el_limite_de_la_ventana_se_acepta():
    assert _normalizar(AHORA - VENTANA) == AHORA - VENTANA


def test_fecha_anterior_a_la_ventana_es_rechazada():
    # Un registro offline sincronizado días después ya habría vencido (D-02).
    with pytest.raises(FechaObservacionInvalidaError):
        _normalizar(AHORA - VENTANA - timedelta(seconds=1))
