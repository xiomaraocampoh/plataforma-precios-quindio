from decimal import Decimal

import pytest

from apps.precios.domain.confianza import NivelConfianza, es_anomalo, nivel_confianza
from apps.precios.domain.vigencia import Fuente

pytestmark = pytest.mark.unit

TOL = Decimal("0.5")
REFERENCIA = [Decimal("4000"), Decimal("4200"), Decimal("4100"), Decimal("3900")]


def test_precio_cercano_a_la_mediana_no_es_anomalo():
    assert not es_anomalo(Decimal("4300"), REFERENCIA, TOL)


@pytest.mark.parametrize("precio", [Decimal("500"), Decimal("9000")])
def test_precio_muy_alejado_es_anomalo(precio):
    assert es_anomalo(precio, REFERENCIA, TOL)


def test_sin_muestras_suficientes_no_se_marca_anomalo():
    assert not es_anomalo(Decimal("100"), [Decimal("4000")], TOL)


def test_anomalo_siempre_es_confianza_baja():
    assert nivel_confianza(Fuente.COMERCIO, 5, anomalo=True) == NivelConfianza.BAJA


def test_reporte_confirmado_por_dos_usuarios_es_confianza_alta():
    assert nivel_confianza(Fuente.REPORTANTE, 2, anomalo=False) == NivelConfianza.ALTA


def test_reporte_aislado_es_confianza_media():
    assert nivel_confianza(Fuente.REPORTANTE, 0, anomalo=False) == NivelConfianza.MEDIA
