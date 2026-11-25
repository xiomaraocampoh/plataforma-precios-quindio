"""Promociones como estrategias (ADR-014, RF-C04). Python puro — TDD.

El orden de la comparación nunca usa estos precios (EC-06): solo se muestran como etiqueta.
«Pague X lleve Y» (aquí, lleve 3 pague 2) se valida con 1, 2, 3 y 7 unidades.
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from apps.catalogo.domain.normalizacion import Unidad
from apps.comercios.domain.promociones import (
    DescuentoPorcentual,
    MotivoPromocion,
    PagueXLleveY,
    PrecioEspecial,
    Promocion,
    PromocionInvalidaError,
    TipoPromocion,
    Vigencia,
    aplicar_a_cantidad,
    estrategia_de,
    exigir_datos_del_motivo,
    precio_efectivo_por_unidad,
)

pytestmark = pytest.mark.unit

INICIO = datetime(2026, 11, 20, tzinfo=UTC)
FIN = datetime(2026, 11, 30, tzinfo=UTC)
DENTRO = datetime(2026, 11, 25, tzinfo=UTC)
VIGENCIA = Vigencia(INICIO, FIN)


def _promo(estrategia, regular="4000") -> Promocion:
    return Promocion(estrategia=estrategia, precio_regular=Decimal(regular), vigencia=VIGENCIA)


# ---------- Vigencia ----------


def test_la_vigencia_incluye_el_inicio_y_excluye_el_fin():
    assert VIGENCIA.vigente_en(INICIO)
    assert VIGENCIA.vigente_en(DENTRO)
    assert not VIGENCIA.vigente_en(FIN)
    assert not VIGENCIA.vigente_en(INICIO - timedelta(seconds=1))


def test_una_promocion_vencida_no_esta_vigente():
    promo = _promo(DescuentoPorcentual(Decimal("10")))
    assert not promo.vigente_en(FIN + timedelta(days=1))


@pytest.mark.parametrize("fin", [INICIO, INICIO - timedelta(days=1)])
def test_el_fin_debe_ser_posterior_al_inicio(fin):
    with pytest.raises(PromocionInvalidaError):
        Vigencia(INICIO, fin)


# ---------- Descuento porcentual ----------


def test_descuento_porcentual_calcula_el_precio_efectivo():
    promo = _promo(DescuentoPorcentual(Decimal("15")), regular="4100")
    assert promo.precio_efectivo() == Decimal("3485.00")
    assert promo.estrategia.tipo == TipoPromocion.DESCUENTO_PORCENTUAL


def test_descuento_porcentual_redondea_a_centavos():
    promo = _promo(DescuentoPorcentual(Decimal("33.33")), regular="1000")
    assert promo.precio_efectivo() == Decimal("666.70")


@pytest.mark.parametrize("porcentaje", ["0", "100", "-5", "150"])
def test_descuento_de_0_o_100_por_ciento_o_fuera_de_rango_se_rechaza(porcentaje):
    # 0 % no es una promoción y 100 % es regalar el producto: ninguno se publica
    with pytest.raises(PromocionInvalidaError):
        DescuentoPorcentual(Decimal(porcentaje))


def test_descuento_casi_total_si_se_acepta():
    assert _promo(DescuentoPorcentual(Decimal("99.99")), "1000").precio_efectivo() == Decimal(
        "0.10"
    )


# ---------- Precio especial ----------


def test_precio_especial_es_el_precio_efectivo():
    promo = _promo(PrecioEspecial(Decimal("3500")))
    assert promo.precio_efectivo() == Decimal("3500")


@pytest.mark.parametrize("especial", ["4000", "4500"])
def test_precio_especial_debe_ser_menor_que_el_regular(especial):
    with pytest.raises(PromocionInvalidaError):
        _promo(PrecioEspecial(Decimal(especial)))


@pytest.mark.parametrize("especial", ["0", "-1"])
def test_precio_especial_debe_ser_positivo(especial):
    with pytest.raises(PromocionInvalidaError):
        PrecioEspecial(Decimal(especial))


@pytest.mark.parametrize("regular", ["0", "-100"])
def test_el_precio_regular_debe_ser_positivo(regular):
    with pytest.raises(PromocionInvalidaError):
        _promo(DescuentoPorcentual(Decimal("10")), regular=regular)


# ---------- Pague X lleve Y ----------


@pytest.mark.parametrize(
    ("cantidad", "total"),
    [(1, "4000"), (2, "8000"), (3, "8000"), (7, "20000")],
)
def test_lleve_3_pague_2_con_1_2_3_y_7_unidades(cantidad, total):
    # 7 = dos grupos de 3 (se pagan 4) + 1 suelta (se paga) → 5 × 4000
    promo = _promo(PagueXLleveY(pague=2, lleve=3))
    resultado = aplicar_a_cantidad(promo, cantidad)
    assert resultado.total == Decimal(total)
    assert resultado.regular == Decimal("4000") * cantidad
    assert resultado.ahorro == resultado.regular - resultado.total


def test_pague_x_lleve_y_promedia_el_precio_por_empaque_llevando_y():
    promo = _promo(PagueXLleveY(pague=2, lleve=3), regular="3000")
    assert promo.precio_efectivo() == Decimal("2000.00")
    assert promo.unidades_minimas == 3


@pytest.mark.parametrize(("pague", "lleve"), [(3, 2), (2, 2), (0, 3), (-1, 2)])
def test_pague_debe_ser_menor_que_lleve_y_positivo(pague, lleve):
    # «pague 3 lleve 2» literal cobraría más de lo que se lleva: no es una promoción
    with pytest.raises(PromocionInvalidaError):
        PagueXLleveY(pague=pague, lleve=lleve)


# ---------- aplicar_a_cantidad (para la canasta, ADR-0029) ----------


def test_aplicar_descuento_a_varias_unidades():
    resultado = aplicar_a_cantidad(_promo(DescuentoPorcentual(Decimal("10"))), 3)
    assert resultado.total == Decimal("10800.00")
    assert resultado.aplicada


def test_aplicar_precio_especial_a_varias_unidades():
    assert aplicar_a_cantidad(_promo(PrecioEspecial(Decimal("3500"))), 2).total == Decimal("7000")


@pytest.mark.parametrize("cantidad", [0, -1])
def test_la_cantidad_debe_ser_al_menos_uno(cantidad):
    with pytest.raises(ValueError):
        aplicar_a_cantidad(_promo(DescuentoPorcentual(Decimal("10"))), cantidad)


def test_aplicar_una_promocion_vencida_cobra_el_precio_regular():
    promo = _promo(PagueXLleveY(pague=2, lleve=3))
    resultado = aplicar_a_cantidad(promo, 3, momento=FIN + timedelta(hours=1))
    assert resultado.total == Decimal("12000")
    assert resultado.ahorro == 0
    assert not resultado.aplicada


def test_aplicar_dentro_de_la_vigencia_si_descuenta():
    promo = _promo(PagueXLleveY(pague=2, lleve=3))
    assert aplicar_a_cantidad(promo, 3, momento=DENTRO).aplicada


# ---------- Precio efectivo por unidad (precio_por_unidad, M-05) ----------


@pytest.mark.parametrize(
    ("regular", "cantidad", "unidad", "esperado", "base"),
    [
        ("4000", "500", "g", "7200.00", Unidad.KILOGRAMO),  # 3600 / 0,5 kg
        ("8000", "1", "kg", "7200.00", Unidad.KILOGRAMO),  # 7200 / 1 kg: lo mismo
        ("4500", "900", "ml", "4500.00", Unidad.LITRO),  # 4050 / 0,9 L
        ("6000", "6", "und", "900.00", Unidad.UNIDAD),
    ],
)
def test_precio_efectivo_por_unidad_con_unidades_distintas(
    regular, cantidad, unidad, esperado, base
):
    promo = _promo(DescuentoPorcentual(Decimal("10")), regular=regular)
    valor, unidad_base = precio_efectivo_por_unidad(promo, Decimal(cantidad), unidad)
    assert valor == Decimal(esperado)
    assert unidad_base == base


def test_precio_efectivo_por_unidad_rechaza_cantidad_cero():
    with pytest.raises(ValueError):
        precio_efectivo_por_unidad(_promo(DescuentoPorcentual(Decimal("10"))), Decimal("0"), "g")


# ---------- Descripción, construcción y motivo ----------


@pytest.mark.parametrize(
    ("estrategia", "texto"),
    [
        (DescuentoPorcentual(Decimal("15")), "15 % de descuento"),
        (DescuentoPorcentual(Decimal("12.5")), "12,5 % de descuento"),
        (PrecioEspecial(Decimal("3500")), "Precio especial de $3.500"),
        (PagueXLleveY(pague=2, lleve=3), "Lleve 3, pague 2"),
    ],
)
def test_cada_estrategia_se_describe_en_palabras(estrategia, texto):
    assert estrategia.describir() == texto


def test_estrategia_de_construye_cada_tipo_desde_sus_datos():
    assert estrategia_de("descuento_porcentual", porcentaje=Decimal("10")) == DescuentoPorcentual(
        Decimal("10")
    )
    assert estrategia_de("precio_especial", precio_especial=Decimal("3000")) == PrecioEspecial(
        Decimal("3000")
    )
    assert estrategia_de("pague_x_lleve_y", pague=2, lleve=3) == PagueXLleveY(2, 3)


@pytest.mark.parametrize(
    ("tipo", "datos"),
    [
        ("descuento_porcentual", {}),
        ("precio_especial", {"porcentaje": Decimal("10")}),
        ("pague_x_lleve_y", {"pague": 2}),
        ("dos_por_uno", {}),
    ],
)
def test_estrategia_de_exige_los_datos_de_su_tipo(tipo, datos):
    with pytest.raises(PromocionInvalidaError):
        estrategia_de(tipo, **datos)


def test_proximo_a_vencer_exige_la_fecha_de_vencimiento():
    with pytest.raises(PromocionInvalidaError):
        exigir_datos_del_motivo(MotivoPromocion.PROXIMO_A_VENCER, None, VIGENCIA)


def test_la_promocion_no_puede_durar_mas_que_el_producto():
    with pytest.raises(PromocionInvalidaError):
        exigir_datos_del_motivo(MotivoPromocion.PROXIMO_A_VENCER, date(2026, 11, 27), VIGENCIA)


def test_proximo_a_vencer_con_fecha_valida_se_acepta():
    exigir_datos_del_motivo(MotivoPromocion.PROXIMO_A_VENCER, date(2026, 11, 30), VIGENCIA)


def test_otros_motivos_no_llevan_fecha_de_vencimiento():
    exigir_datos_del_motivo(MotivoPromocion.TEMPORADA, None, VIGENCIA)
    with pytest.raises(PromocionInvalidaError):
        exigir_datos_del_motivo(MotivoPromocion.TEMPORADA, date(2026, 12, 1), VIGENCIA)
