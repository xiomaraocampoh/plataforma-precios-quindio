"""Canasta: total por establecimiento, faltantes y orden declarado (ADR-0027 a 0029).

M-24 (totales y faltantes correctos), M-05 (conversión de unidades), M-06 (orden neutral).
"""

from decimal import Decimal

import pytest

from apps.canasta.domain.canasta import (
    MAX_ITEMS,
    CanastaInvalidaError,
    ItemCanasta,
    OfertaPresentacion,
    calcular_canasta,
    ordenar_opciones,
    texto_criterio,
    validar_items,
)

pytestmark = pytest.mark.unit

ARROZ, LECHE = 1, 2
TIENDAS = {10: "Tienda Doña Rosa", 20: "Súper Quindío", 30: "Éxito Centro"}


def _item(pid=ARROZ, cantidad="1", unidad="kg", nombre="Arroz"):
    return ItemCanasta(producto_id=pid, nombre=nombre, cantidad=Decimal(cantidad), unidad=unidad)


def _oferta(est, pid, precio, tamano="1", unidad="kg", presentacion=None):
    return OfertaPresentacion(
        establecimiento_id=est,
        producto_id=pid,
        presentacion_id=presentacion or pid * 100 + int(Decimal(tamano) * 10),
        tamano=Decimal(tamano),
        unidad=unidad,
        precio=Decimal(precio),
    )


def _por_id(opciones):
    return {o.establecimiento_id: o for o in opciones}


# --- validación del pedido (M-02, M-05) --------------------------------------------------------
def test_cantidad_cero_o_negativa_se_rechaza():
    for malo in ("0", "-1"):
        with pytest.raises(CanastaInvalidaError):
            validar_items([_item(cantidad=malo)], {ARROZ: {"kg", "g"}})


def test_unidad_incompatible_con_el_producto_se_rechaza():
    with pytest.raises(CanastaInvalidaError, match="Arroz"):
        validar_items([_item(unidad="L")], {ARROZ: {"kg", "g"}})


def test_g_y_kg_son_compatibles():
    validar_items([_item(cantidad="500", unidad="g")], {ARROZ: {"kg"}})


def test_producto_repetido_se_rechaza():
    with pytest.raises(CanastaInvalidaError):
        validar_items([_item(), _item()], {ARROZ: {"kg"}})


def test_canasta_vacia_y_mas_de_20_productos_se_rechazan():
    with pytest.raises(CanastaInvalidaError):
        validar_items([], {})
    muchos = [_item(pid=i, nombre=f"P{i}") for i in range(MAX_ITEMS + 1)]
    with pytest.raises(CanastaInvalidaError):
        validar_items(muchos, {i: {"kg"} for i in range(MAX_ITEMS + 1)})


# --- cálculo del total -------------------------------------------------------------------------
def test_total_es_cantidad_en_unidad_base_por_precio_por_unidad():
    # 2 kg a $6.000 el kg = $12.000
    opciones = calcular_canasta([_item(cantidad="2")], [_oferta(10, ARROZ, "6000")], TIENDAS)
    assert opciones[0].total == Decimal("12000.00")


def test_convierte_gramos_a_kilos():
    # 500 g de un arroz de 1 kg a $6.000 → 0,5 kg × 6.000 = 3.000
    opciones = calcular_canasta(
        [_item(cantidad="500", unidad="g")], [_oferta(10, ARROZ, "6000")], TIENDAS
    )
    assert opciones[0].total == Decimal("3000.00")


def test_usa_la_presentacion_de_menor_precio_por_unidad_del_comercio():
    ofertas = [
        _oferta(10, ARROZ, "3500", tamano="500", unidad="g"),  # 7.000/kg
        _oferta(10, ARROZ, "6000", tamano="1", unidad="kg"),  # 6.000/kg  ← la elegida
    ]
    linea = calcular_canasta([_item(cantidad="2")], ofertas, TIENDAS)[0].lineas[0]
    assert linea.tamano == Decimal("1") and linea.unidad_presentacion == "kg"
    assert linea.costo == Decimal("12000.00")


def test_empate_de_precio_por_unidad_elige_la_de_menor_tamano():
    ofertas = [
        _oferta(10, ARROZ, "6000", tamano="1", unidad="kg", presentacion=2),
        _oferta(10, ARROZ, "3000", tamano="500", unidad="g", presentacion=1),
    ]
    linea = calcular_canasta([_item()], ofertas, TIENDAS)[0].lineas[0]
    assert linea.presentacion_id == 1


def test_empaques_sugeridos_se_redondean_hacia_arriba_sin_sumar_el_sobrante():
    # 1,2 kg con empaques de 1 kg → 2 empaques, pero el costo es de 1,2 kg
    linea = calcular_canasta([_item(cantidad="1.2")], [_oferta(10, ARROZ, "5000")], TIENDAS)[
        0
    ].lineas[0]
    assert linea.empaques == 2
    assert linea.costo == Decimal("6000.00")


def test_redondeo_a_centavos_half_up_por_producto():
    # $1.000 / 3 kg = 333,33 el kg; 1 kg → 333,33
    linea = calcular_canasta(
        [_item(cantidad="1")], [_oferta(10, ARROZ, "1000", tamano="3")], TIENDAS
    )[0].lineas[0]
    assert linea.costo == Decimal("333.33")


# --- productos sin precio (M-24) ---------------------------------------------------------------
def test_un_producto_sin_precio_no_se_suma_como_cero_y_se_lista_como_faltante():
    items = [_item(ARROZ), _item(LECHE, unidad="L", nombre="Leche")]
    opciones = _por_id(calcular_canasta(items, [_oferta(10, ARROZ, "6000")], TIENDAS))
    o = opciones[10]
    assert o.total == Decimal("6000.00")
    assert [f.nombre for f in o.faltantes] == ["Leche"]
    assert (o.disponibles, o.pedidos) == (1, 2)
    assert o.cobertura == "1 de 2"


def test_un_establecimiento_sin_ningun_precio_de_la_canasta_no_aparece():
    opciones = calcular_canasta([_item()], [_oferta(10, ARROZ, "6000")], TIENDAS)
    assert [o.establecimiento_id for o in opciones] == [10]


def test_oferta_de_otra_magnitud_no_cuenta_como_precio():
    opciones = calcular_canasta(
        [_item()], [_oferta(10, ARROZ, "3000", tamano="1", unidad="L")], TIENDAS
    )
    assert opciones == []


# --- orden declarado (ADR-0028, EC-06) ---------------------------------------------------------
def _escenario():
    items = [_item(ARROZ), _item(LECHE, unidad="L", nombre="Leche")]
    ofertas = [
        _oferta(10, ARROZ, "5000"),  # barata pero incompleta
        _oferta(20, ARROZ, "6000"),
        _oferta(20, LECHE, "4000", unidad="L"),  # completa, total 10.000
        _oferta(30, ARROZ, "6500"),
        _oferta(30, LECHE, "3000", unidad="L"),  # completa, total 9.500
    ]
    return calcular_canasta(items, ofertas, TIENDAS)


def test_por_cobertura_primero_las_completas_y_luego_menor_total():
    orden = [o.establecimiento_id for o in ordenar_opciones(_escenario(), "cobertura")]
    assert orden == [30, 20, 10]


def test_por_total_gana_la_mas_barata_aunque_este_incompleta():
    orden = [o.establecimiento_id for o in ordenar_opciones(_escenario(), "total")]
    assert orden == [10, 30, 20]


def test_empate_total_y_cobertura_desempata_por_nombre_sin_tildes_ni_mayusculas_y_luego_id():
    items = [_item()]
    ofertas = [_oferta(e, ARROZ, "6000") for e in (10, 20, 30)]
    nombres = {10: "zeta", 20: "Éxito", 30: "ÉXITO"}
    orden = [
        o.establecimiento_id for o in ordenar_opciones(calcular_canasta(items, ofertas, nombres))
    ]
    assert orden == [20, 30, 10]


def test_el_criterio_es_declarado_y_desconocido_falla():
    assert "más productos disponibles" in texto_criterio("cobertura")
    assert "menor total" in texto_criterio("total")
    with pytest.raises(ValueError):
        ordenar_opciones(_escenario(), "patrocinio")
