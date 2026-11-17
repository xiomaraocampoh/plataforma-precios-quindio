"""«visto hace …» en la comparación: una sola unidad, sin comas pegadas."""

from datetime import datetime, timedelta

import pytest

from apps.comparacion.templatetags.tiempo import hace

pytestmark = pytest.mark.unit

AHORA = datetime(2026, 11, 16, 20, 0)


@pytest.mark.parametrize(
    ("atras", "esperado"),
    [
        (timedelta(hours=19, minutes=50), "19 horas"),
        (timedelta(days=2, hours=3), "2 días"),
        (timedelta(minutes=5), "5 minutos"),
        (timedelta(seconds=20), "instantes"),
        (timedelta(0), "instantes"),
    ],
)
def test_hace_usa_una_sola_unidad(atras, esperado):
    assert hace(AHORA - atras, AHORA).replace("\xa0", " ") == esperado


def test_hace_nunca_deja_una_coma_pegada():
    assert "," not in hace(AHORA - timedelta(hours=19, minutes=50), AHORA)
