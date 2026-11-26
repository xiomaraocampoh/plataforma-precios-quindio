"""Precio oficial verificado frente a lo reportado (ADR-018, RF-C05).

Discrepancia: al menos 2 reportes de usuarios en los últimos 7 días que difieren MÁS de 10 % del
precio oficial. Entonces se muestra «Usuarios reportan $X» con el más reciente de ellos.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from apps.comparacion.domain.oficial import (
    DIAS_DISCREPANCIA,
    MIN_REPORTES_DISCREPANTES,
    UMBRAL_DISCREPANCIA,
    discrepancia,
)

pytestmark = pytest.mark.unit

AHORA = datetime(2026, 11, 25, 12, tzinfo=UTC)
OFICIAL = Decimal("4000")


def _hace(dias: float) -> datetime:
    return AHORA - timedelta(days=dias)


def test_las_constantes_son_las_del_adr_018():
    assert UMBRAL_DISCREPANCIA == Decimal("0.10")
    assert MIN_REPORTES_DISCREPANTES == 2
    assert DIAS_DISCREPANCIA == 7


def test_sin_reportes_no_hay_discrepancia():
    assert discrepancia(OFICIAL, [], AHORA) is None


def test_un_solo_reporte_discrepante_no_basta():
    assert discrepancia(OFICIAL, [(Decimal("5000"), _hace(1))], AHORA) is None


def test_dos_reportes_discrepantes_muestran_el_mas_reciente():
    reportes = [(Decimal("5000"), _hace(3)), (Decimal("5200"), _hace(1))]
    assert discrepancia(OFICIAL, reportes, AHORA) == Decimal("5200")


def test_la_discrepancia_funciona_hacia_abajo_tambien():
    reportes = [(Decimal("3000"), _hace(2)), (Decimal("3100"), _hace(1))]
    assert discrepancia(OFICIAL, reportes, AHORA) == Decimal("3100")


def test_exactamente_10_por_ciento_no_es_discrepancia():
    # «más de 10 %»: 4400 y 3600 están justo en el límite
    reportes = [(Decimal("4400"), _hace(1)), (Decimal("3600"), _hace(2))]
    assert discrepancia(OFICIAL, reportes, AHORA) is None


def test_un_centavo_por_encima_del_limite_si_cuenta():
    reportes = [(Decimal("4400.01"), _hace(1)), (Decimal("3599.99"), _hace(2))]
    assert discrepancia(OFICIAL, reportes, AHORA) == Decimal("4400.01")


def test_los_reportes_de_hace_mas_de_7_dias_no_cuentan():
    reportes = [(Decimal("5000"), _hace(7.01)), (Decimal("5200"), _hace(1))]
    assert discrepancia(OFICIAL, reportes, AHORA) is None


def test_el_dia_7_exacto_todavia_cuenta():
    reportes = [(Decimal("5000"), _hace(7)), (Decimal("5200"), _hace(1))]
    assert discrepancia(OFICIAL, reportes, AHORA) == Decimal("5200")


def test_los_reportes_que_coinciden_con_el_oficial_no_cuentan():
    reportes = [
        (Decimal("4000"), _hace(1)),
        (Decimal("4100"), _hace(1)),
        (Decimal("5000"), _hace(2)),
    ]
    assert discrepancia(OFICIAL, reportes, AHORA) is None


def test_un_reporte_con_fecha_futura_cuenta_como_ahora():
    reportes = [(Decimal("5000"), AHORA + timedelta(minutes=5)), (Decimal("5100"), _hace(1))]
    assert discrepancia(OFICIAL, reportes, AHORA) == Decimal("5000")


@pytest.mark.parametrize("oficial", [Decimal("0"), Decimal("-1")])
def test_el_precio_oficial_debe_ser_positivo(oficial):
    with pytest.raises(ValueError):
        discrepancia(oficial, [], AHORA)
