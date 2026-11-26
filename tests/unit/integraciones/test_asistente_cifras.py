"""K-nasta: la IA no puede inventar cifras (EC-14, ADR-0030). Python puro."""

import pytest

from apps.integraciones.domain.asistente import cifras_permitidas, texto_sin_cifras_inventadas

pytestmark = pytest.mark.unit

RESULTADO = '{"total": 30841, "total_texto": "$30.841", "cobertura": "3 de 3", "cantidad": 2}'


def _ok(texto, *fuentes):
    return texto_sin_cifras_inventadas(texto, cifras_permitidas(*fuentes))


def test_acepta_una_cifra_que_salio_del_calculo():
    assert _ok("Te sale en $30.841 en total.", RESULTADO)


def test_acepta_la_misma_cifra_con_otro_formato():
    assert _ok("Son 30841 pesos.", RESULTADO)
    assert _ok("Serían $30,841.", RESULTADO)


def test_rechaza_un_precio_inventado():
    assert not _ok("Te sale en $29.900 en total.", RESULTADO)


def test_rechaza_cualquier_monto_con_signo_pesos_aunque_sea_pequeno():
    assert not _ok("Cuesta $50 más.", RESULTADO)


def test_cifras_pequenas_sin_signo_no_son_dinero():
    assert _ok("Tiene 3 de 3 productos, unos 2 kilos.", RESULTADO)


def test_un_numero_largo_sin_signo_pesos_tambien_cuenta():
    assert not _ok("El arroz vale 7500 en esa tienda.", RESULTADO)


def test_sin_resultados_ningun_monto_es_valido():
    assert not _ok("Te sale en $30.841.")
    assert _ok("¿Qué vas a comprar esta semana?")


def test_las_cantidades_que_la_persona_pidio_y_salieron_del_calculo_son_validas():
    assert _ok("Llevarías 500 g de café.", '{"cantidad": 500, "unidad": "g"}')


def test_varias_fuentes_se_suman():
    assert _ok("Total $30.841 y alternativa $35.000.", RESULTADO, '{"total": 35000}')


def test_las_instrucciones_piden_no_asumir_el_genero_de_la_persona():
    from apps.integraciones.domain.asistente import INSTRUCCIONES

    assert "No asumas el género" in INSTRUCCIONES and "bienvenida" in INSTRUCCIONES
