from datetime import UTC, datetime, timedelta

import pytest

from apps.precios.domain.vigencia import Fuente, PoliticaVigencia, es_vigente

pytestmark = pytest.mark.unit

AHORA = datetime(2026, 11, 15, 12, 0, tzinfo=UTC)


def test_reporte_de_hace_7_dias_sigue_vigente():
    assert es_vigente(AHORA - timedelta(days=7), AHORA)


def test_reporte_de_hace_mas_de_7_dias_vence():
    assert not es_vigente(AHORA - timedelta(days=7, seconds=1), AHORA)


def test_perecedero_vence_a_los_3_dias():
    assert es_vigente(AHORA - timedelta(days=3), AHORA, perecedero=True)
    assert not es_vigente(AHORA - timedelta(days=4), AHORA, perecedero=True)


def test_precio_oficial_de_comercio_dura_30_dias():
    assert es_vigente(AHORA - timedelta(days=29), AHORA, Fuente.COMERCIO)
    assert not es_vigente(AHORA - timedelta(days=31), AHORA, Fuente.COMERCIO)


def test_politica_es_parametrizable():
    politica = PoliticaVigencia(dias_reporte=2)
    assert not es_vigente(AHORA - timedelta(days=3), AHORA, politica=politica)


def test_fecha_futura_es_error():
    with pytest.raises(ValueError):
        es_vigente(AHORA + timedelta(minutes=1), AHORA)
