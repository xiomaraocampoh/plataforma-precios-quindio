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


# ---------- «Ver en el mapa» en la tarjeta: coordenadas o, si faltan, búsqueda por dirección ----------


def test_enlace_mapa_prefiere_las_coordenadas():
    from apps.establecimientos.domain.mapas import enlace_mapa

    enlace = enlace_mapa(
        Decimal("4.53"),
        Decimal("-75.68"),
        direccion="Cl. 19 # 17-27",
        barrio="",
        municipio="Armenia",
    )
    assert enlace.startswith("https://www.openstreetmap.org/?mlat=4.53")


def test_sin_coordenadas_busca_la_direccion_en_el_quindio():
    from apps.establecimientos.domain.mapas import enlace_mapa

    enlace = enlace_mapa(
        None, None, direccion="Cl. 19 # 17-27", barrio="Centro", municipio="Armenia"
    )
    assert enlace == (
        "https://www.openstreetmap.org/search?query="
        "Cl.%2019%20%23%2017-27%2C%20Centro%2C%20Armenia%2C%20Quind%C3%ADo%2C%20Colombia"
    )


def test_sin_coordenadas_ni_direccion_no_hay_enlace():
    from apps.establecimientos.domain.mapas import enlace_mapa

    assert enlace_mapa(None, None, direccion=" ", barrio="", municipio="") is None
