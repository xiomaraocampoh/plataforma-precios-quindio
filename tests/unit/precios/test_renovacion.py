"""RF-14 «Sigue igual»: una confirmación renueva la vigencia del precio (EC-02, D-02)."""

from datetime import UTC, datetime, timedelta

import pytest

from apps.precios.domain.vigencia import es_vigente, fecha_de_referencia

pytestmark = pytest.mark.unit

AHORA = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
HACE_8_DIAS = AHORA - timedelta(days=8)


def test_sin_confirmaciones_la_referencia_es_la_observacion():
    assert fecha_de_referencia(HACE_8_DIAS, []) == HACE_8_DIAS


def test_la_confirmacion_mas_reciente_renueva_la_referencia():
    confirmaciones = [AHORA - timedelta(days=3), AHORA - timedelta(days=1)]
    assert fecha_de_referencia(HACE_8_DIAS, confirmaciones) == AHORA - timedelta(days=1)


def test_una_confirmacion_anterior_a_la_observacion_no_la_retrasa():
    assert fecha_de_referencia(HACE_8_DIAS, [HACE_8_DIAS - timedelta(days=2)]) == HACE_8_DIAS


def test_un_precio_vencido_vuelve_a_ser_vigente_si_alguien_lo_confirma():
    # Reportado hace 8 días (ventana de 7): vencido; confirmado ayer: vigente otra vez
    assert not es_vigente(HACE_8_DIAS, AHORA)
    renovado = fecha_de_referencia(HACE_8_DIAS, [AHORA - timedelta(days=1)])
    assert es_vigente(renovado, AHORA)
