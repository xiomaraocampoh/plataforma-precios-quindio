"""Puerto de extensiones de la comparación (ADR-012, DP-1 opción B).

La comparación define QUÉ datos comerciales acepta; no sabe quién los aporta. Con el puerto vacío
la comparación funciona igual que el núcleo del Corte 2.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from apps.comparacion.domain.extensiones import (
    PUNTO_DATOS_COMERCIALES,
    DatosComerciales,
    ExtensionComparacion,
    PrecioOficialVigente,
    PromocionComparacion,
    reunir_datos,
)

pytestmark = pytest.mark.unit

AHORA = datetime(2026, 11, 25, 12, tzinfo=UTC)


def _oficial(eid=1, pid=10, precio="4100") -> PrecioOficialVigente:
    return PrecioOficialVigente(
        producto_id=7,
        establecimiento_id=eid,
        presentacion_id=pid,
        precio=Decimal(precio),
        confirmado_en=AHORA,
    )


def _promo(eid=1, pid=10) -> PromocionComparacion:
    return PromocionComparacion(
        producto_id=7,
        establecimiento_id=eid,
        presentacion_id=pid,
        tipo="descuento_porcentual",
        descripcion="10 % de descuento",
        precio_efectivo=Decimal("3690"),
        precio_efectivo_unitario=Decimal("7380"),
        unidad_base="kg",
        inicio=AHORA,
        fin=AHORA,
        motivo="temporada",
        condiciones="Hasta agotar existencias.",
        fecha_vencimiento_producto=None,
    )


class _Fija:
    def __init__(self, datos: DatosComerciales):
        self.datos = datos
        self.pedidos: list[tuple] = []

    def datos_para(self, producto_ids, ahora):
        self.pedidos.append((tuple(producto_ids), ahora))
        return self.datos


def test_el_punto_tiene_un_nombre_estable():
    assert PUNTO_DATOS_COMERCIALES == "comparacion.datos_comerciales"


def test_sin_extensiones_no_hay_datos_comerciales():
    datos = reunir_datos([], [7], AHORA)
    assert datos == DatosComerciales()
    assert datos.oficiales == () and datos.promociones == ()


def test_una_extension_que_cumple_el_protocolo_se_consulta_con_los_productos_y_la_hora():
    extension = _Fija(DatosComerciales(oficiales=(_oficial(),)))
    assert isinstance(extension, ExtensionComparacion)  # Protocol en tiempo de ejecución
    datos = reunir_datos([extension], [7, 8], AHORA)
    assert extension.pedidos == [((7, 8), AHORA)]
    assert datos.oficiales == (_oficial(),)


def test_los_datos_de_varias_extensiones_se_suman_en_orden_de_registro():
    a = _Fija(DatosComerciales(oficiales=(_oficial(eid=1),)))
    b = _Fija(DatosComerciales(oficiales=(_oficial(eid=2),), promociones=(_promo(),)))
    datos = reunir_datos([a, b], [7], AHORA)
    assert [o.establecimiento_id for o in datos.oficiales] == [1, 2]
    assert datos.promociones == (_promo(),)


def test_sin_productos_no_se_consulta_a_nadie():
    extension = _Fija(DatosComerciales(oficiales=(_oficial(),)))
    assert reunir_datos([extension], [], AHORA) == DatosComerciales()
    assert extension.pedidos == []


def test_un_objeto_sin_datos_para_no_es_una_extension():
    assert not isinstance(object(), ExtensionComparacion)


def test_los_datos_se_agrupan_por_establecimiento_y_presentacion():
    datos = DatosComerciales(
        oficiales=(_oficial(eid=1, pid=10), _oficial(eid=2, pid=10)),
        promociones=(_promo(eid=1, pid=10), _promo(eid=1, pid=10), _promo(eid=2, pid=11)),
    )
    assert set(datos.oficiales_por_par()) == {(1, 10), (2, 10)}
    promos = datos.promociones_por_par()
    assert len(promos[(1, 10)]) == 2 and len(promos[(2, 11)]) == 1
