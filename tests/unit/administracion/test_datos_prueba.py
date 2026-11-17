"""Lectura y validación de las filas CSV de los datos de prueba (data/demo/). Dominio puro."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from apps.administracion.domain.datos_prueba import (
    FilaInvalidaError,
    fecha_de_observacion,
    leer_cantidad,
    leer_establecimiento,
    leer_fuente,
    leer_precio,
    leer_presentacion,
    leer_si_no,
    leer_unidad,
)

pytestmark = pytest.mark.unit

AHORA = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)


class TestUnidad:
    @pytest.mark.parametrize(
        ("texto", "esperada"),
        [("g", "g"), ("KG", "kg"), (" ml ", "ml"), ("l", "L"), ("L", "L"), ("und", "und")],
    )
    def test_acepta_las_unidades_del_catalogo(self, texto, esperada):
        assert leer_unidad(texto) == esperada

    @pytest.mark.parametrize("texto", ["", "lb", "oz", "unidad", "gr"])
    def test_rechaza_unidades_desconocidas(self, texto):
        with pytest.raises(FilaInvalidaError, match="unidad"):
            leer_unidad(texto)


class TestNumeros:
    def test_precio_es_decimal_exacto(self):
        assert leer_precio("4100") == Decimal("4100")
        assert leer_precio("6480.50") == Decimal("6480.50")

    @pytest.mark.parametrize("texto", ["0", "-50", "abc", "", "1e3", "4.100,00"])
    def test_precio_invalido_cero_o_negativo(self, texto):
        with pytest.raises(FilaInvalidaError, match="precio"):
            leer_precio(texto)

    def test_cantidad_positiva(self):
        assert leer_cantidad("0.5") == Decimal("0.5")
        with pytest.raises(FilaInvalidaError, match="cantidad"):
            leer_cantidad("0")


class TestFuente:
    def test_reportante_y_oficial(self):
        # «oficial» es el precio publicado por el propio comercio: fuente «comercio» del dominio
        assert leer_fuente("reportante") == "reportante"
        assert leer_fuente("Oficial") == "comercio"

    def test_fuente_desconocida(self):
        with pytest.raises(FilaInvalidaError, match="fuente"):
            leer_fuente("sipsa")


class TestSiNo:
    @pytest.mark.parametrize(("texto", "valor"), [("si", True), ("Sí", True), ("no", False)])
    def test_lee_si_y_no(self, texto, valor):
        assert leer_si_no(texto, campo="perecedera") is valor

    def test_vacio_es_no(self):
        assert leer_si_no("", campo="perecedera") is False

    def test_otro_texto_es_error(self):
        with pytest.raises(FilaInvalidaError, match="perecedera"):
            leer_si_no("quizás", campo="perecedera")


class TestFecha:
    def test_dias_y_horas_atras(self):
        assert fecha_de_observacion(AHORA, dias="8", horas="0") == AHORA - timedelta(days=8)
        assert fecha_de_observacion(AHORA, dias="0", horas="5") == AHORA - timedelta(hours=5)

    def test_vacio_es_cero(self):
        assert fecha_de_observacion(AHORA, dias="", horas="") == AHORA

    @pytest.mark.parametrize(("dias", "horas"), [("-1", "0"), ("0", "-2"), ("x", "0")])
    def test_no_admite_fechas_futuras_ni_texto(self, dias, horas):
        with pytest.raises(FilaInvalidaError, match="días|horas"):
            fecha_de_observacion(AHORA, dias=dias, horas=horas)


class TestPresentacion:
    def test_fila_valida(self):
        fila = leer_presentacion(
            {
                "producto": "Arroz blanco premium",
                "marca": "Diana",
                "cantidad": "500",
                "unidad": "g",
                "codigo_barras": "7702511000014",
            }
        )
        assert fila.cantidad == Decimal("500") and fila.unidad == "g"
        assert fila.codigo_barras == "7702511000014"

    def test_codigo_de_barras_invalido(self):
        with pytest.raises(FilaInvalidaError, match="código de barras"):
            leer_presentacion(
                {
                    "producto": "Arroz",
                    "marca": "Diana",
                    "cantidad": "1",
                    "unidad": "kg",
                    "codigo_barras": "7702511000015",  # dígito de control incorrecto
                }
            )

    def test_sin_codigo_de_barras(self):
        fila = leer_presentacion(
            {"producto": "Arroz", "marca": "Roa", "cantidad": "1", "unidad": "kg"}
        )
        assert fila.codigo_barras == ""


class TestEstablecimiento:
    BASE = {
        "nombre": "Tienda Doña Gloria",
        "tipo": "tienda",
        "direccion": "Cl. 10 # 20-30",
        "barrio": "La Clarita",
        "municipio": "Armenia",
        "ficticia": "si",
    }

    def test_fila_valida(self):
        fila = leer_establecimiento(self.BASE)
        assert fila.ficticia is True and fila.tipo == "tienda"

    @pytest.mark.parametrize("tipo", ["supermercado", "discount", "plaza", "minimercado"])
    def test_tipos_admitidos(self, tipo):
        assert leer_establecimiento({**self.BASE, "tipo": tipo}).tipo == tipo

    def test_tipo_desconocido(self):
        with pytest.raises(FilaInvalidaError, match="tipo"):
            leer_establecimiento({**self.BASE, "tipo": "mayorista"})

    @pytest.mark.parametrize("campo", ["nombre", "direccion", "municipio"])
    def test_campos_obligatorios(self, campo):
        with pytest.raises(FilaInvalidaError, match=campo):
            leer_establecimiento({**self.BASE, campo: "  "})
