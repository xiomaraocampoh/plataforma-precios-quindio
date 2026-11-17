"""Textos de la tarjeta de precio (RF-16): fuente, confianza, antigüedad y precio por unidad."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from apps.comparacion.domain.tarjeta import (
    AYUDA_POR_UNIDAD,
    antiguedad,
    etiqueta_fuente,
    formatear_pesos,
    texto_confianza,
    texto_por_unidad,
)

pytestmark = pytest.mark.unit

AHORA = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)


class TestPesos:
    @pytest.mark.parametrize(
        ("valor", "texto"),
        [
            (Decimal("4100"), "$4.100"),
            (Decimal("950"), "$950"),
            (Decimal("26150.00"), "$26.150"),
            (Decimal("1234567"), "$1.234.567"),
            (Decimal("4099.50"), "$4.100"),  # sin centavos: redondeo a la unidad, mitad arriba
            (Decimal("0.4"), "$0"),
        ],
    )
    def test_separador_de_miles_colombiano(self, valor, texto):
        assert formatear_pesos(valor) == texto

    def test_negativo_es_error(self):
        with pytest.raises(ValueError):
            formatear_pesos(Decimal("-1"))


class TestPorUnidad:
    @pytest.mark.parametrize(
        ("unidad", "texto"),
        [("kg", "$4.100 por kg"), ("L", "$4.100 por litro"), ("und", "$4.100 por unidad")],
    )
    def test_dice_la_unidad(self, unidad, texto):
        assert texto_por_unidad(Decimal("4100"), unidad) == texto

    def test_unidad_desconocida(self):
        with pytest.raises(ValueError):
            texto_por_unidad(Decimal("1"), "g")  # la base de comparación nunca es g

    def test_ayuda_breve(self):
        assert AYUDA_POR_UNIDAD == "para comparar empaques de distinto tamaño"


class TestFuente:
    @pytest.mark.parametrize(
        ("fuente", "texto"),
        [
            ("reportante", "Reportado por usuarios"),
            ("comercio", "Oficial del comercio"),
            ("sipsa", "Referencia SIPSA"),
        ],
    )
    def test_etiquetas(self, fuente, texto):
        assert etiqueta_fuente(fuente) == texto

    def test_fuente_desconocida_no_se_inventa(self):
        assert etiqueta_fuente("otra") == "Fuente sin identificar"


class TestConfianza:
    @pytest.mark.parametrize("nivel", ["alta", "media", "baja"])
    def test_siempre_hay_texto_no_solo_color(self, nivel):
        titulo, detalle = texto_confianza(nivel)
        assert titulo == f"Confianza {nivel}"
        assert detalle

    def test_baja_pide_verificar(self):
        assert "verifica" in texto_confianza("baja")[1].lower()

    def test_nivel_desconocido(self):
        with pytest.raises(ValueError):
            texto_confianza("altísima")


class TestAntiguedad:
    @pytest.mark.parametrize(
        ("delta", "texto"),
        [
            (timedelta(seconds=30), "hace un momento"),
            (timedelta(minutes=1), "hace 1 minuto"),
            (timedelta(minutes=45), "hace 45 minutos"),
            (timedelta(hours=1, minutes=10), "hace 1 hora"),
            (timedelta(hours=23), "hace 23 horas"),
            (timedelta(days=1, hours=2), "hace 1 día"),
            (timedelta(days=2), "hace 2 días"),
            (timedelta(days=29), "hace 29 días"),
        ],
    )
    def test_texto_humano(self, delta, texto):
        assert antiguedad(AHORA - delta, AHORA) == texto

    def test_reloj_adelantado_cuenta_como_ahora(self):
        assert antiguedad(AHORA + timedelta(minutes=3), AHORA) == "hace un momento"
