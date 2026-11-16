"""RF-09: enlace a OpenStreetMap con las coordenadas del establecimiento (sin API key)."""

from decimal import Decimal

import pytest

from apps.establecimientos.domain.mapas import enlace_openstreetmap

pytestmark = pytest.mark.unit


def test_enlace_con_marcador_y_zoom_de_calle():
    assert enlace_openstreetmap(Decimal("4.533889"), Decimal("-75.681111")) == (
        "https://www.openstreetmap.org/?mlat=4.533889&mlon=-75.681111#map=18/4.533889/-75.681111"
    )


def test_sin_coordenadas_no_hay_enlace():
    assert enlace_openstreetmap(None, Decimal("-75.68")) is None
    assert enlace_openstreetmap(Decimal("4.53"), None) is None


@pytest.mark.parametrize(
    ("latitud", "longitud"),
    [
        (Decimal("90.1"), Decimal("0")),
        (Decimal("-91"), Decimal("0")),
        (Decimal("0"), Decimal("180.5")),
    ],
)
def test_coordenadas_fuera_de_rango_se_rechazan(latitud, longitud):
    with pytest.raises(ValueError):
        enlace_openstreetmap(latitud, longitud)


def test_el_zoom_es_parametrizable():
    assert enlace_openstreetmap(Decimal("4.5"), Decimal("-75.6"), zoom=15).endswith(
        "#map=15/4.5/-75.6"
    )
