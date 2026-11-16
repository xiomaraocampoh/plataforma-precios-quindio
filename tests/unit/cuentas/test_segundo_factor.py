"""Verificación en dos pasos: códigos, intentos, bloqueo y códigos de respaldo (RF-27)."""

from datetime import UTC, datetime, timedelta

import pytest

from apps.cuentas.domain.segundo_factor import (
    BLOQUEO,
    MAX_INTENTOS,
    VIGENCIA_CODIGO,
    EstadoIntentos,
    Resultado,
    buscar_respaldo,
    evaluar,
    generar_codigo,
    generar_codigos_respaldo,
    hash_codigo,
    pedir_segundo_factor,
    segundo_factor_obligatorio,
)

pytestmark = pytest.mark.unit

CLAVE = "clave-de-prueba"
AHORA = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
VENCE = AHORA + VIGENCIA_CODIGO


def _evaluar(correcto=True, estado=None, ahora=AHORA, vence_en=VENCE):
    return evaluar(
        es_correcto=lambda: correcto,
        estado=estado or EstadoIntentos(),
        ahora=ahora,
        vence_en=vence_en,
    )


def test_el_codigo_tiene_seis_digitos_con_ceros_a_la_izquierda():
    assert generar_codigo(lambda tope: 42) == "000042"
    assert generar_codigo(lambda tope: tope - 1) == "999999"
    codigo = generar_codigo()
    assert len(codigo) == 6 and codigo.isdigit()


def test_solo_se_guarda_el_hash_y_no_revela_el_codigo():
    h = hash_codigo("123456", clave=CLAVE)
    assert "123456" not in h and len(h) == 64
    assert h == hash_codigo(" 123 456 ", clave=CLAVE)  # espacios que agrega el celular
    assert h != hash_codigo("123456", clave="otra-clave")


def test_codigo_correcto_y_vigente_es_valido_y_limpia_los_fallos():
    resultado, estado = _evaluar(estado=EstadoIntentos(intentos_fallidos=3))
    assert resultado == Resultado.VALIDO
    assert estado == EstadoIntentos()


def test_codigo_vencido_a_los_diez_minutos():
    resultado, _ = _evaluar(ahora=VENCE + timedelta(seconds=1))
    assert resultado == Resultado.VENCIDO


def test_cinco_fallos_bloquean_quince_minutos():
    estado = EstadoIntentos()
    for _ in range(MAX_INTENTOS - 1):
        resultado, estado = _evaluar(correcto=False, estado=estado)
        assert resultado == Resultado.INCORRECTO
    resultado, estado = _evaluar(correcto=False, estado=estado)
    assert resultado == Resultado.BLOQUEADO
    assert estado.bloqueado_hasta == AHORA + BLOQUEO


def test_bloqueado_no_acepta_ni_el_codigo_correcto_hasta_que_pase_el_bloqueo():
    bloqueado = EstadoIntentos(bloqueado_hasta=AHORA + BLOQUEO)
    comparaciones = []

    def comparar():
        comparaciones.append(1)
        return True

    resultado, _ = evaluar(es_correcto=comparar, estado=bloqueado, ahora=AHORA, vence_en=None)
    assert resultado == Resultado.BLOQUEADO
    assert comparaciones == []  # bloqueado: ni siquiera se compara el código
    despues = AHORA + BLOQUEO + timedelta(seconds=1)
    resultado, _ = _evaluar(estado=bloqueado, ahora=despues, vence_en=None)
    assert resultado == Resultado.VALIDO


def test_diez_codigos_de_respaldo_distintos_y_de_un_solo_uso():
    codigos = generar_codigos_respaldo()
    assert len(codigos) == 10 and len(set(codigos)) == 10
    assert all(len(c) == 9 and c[4] == "-" for c in codigos)
    hashes = [hash_codigo(c, clave=CLAVE) for c in codigos]
    escrito_a_mano = codigos[3].upper().replace("-", " ")
    assert buscar_respaldo(escrito_a_mano, hashes, clave=CLAVE) == 3
    hashes[3] = ""  # ya usado
    assert buscar_respaldo(codigos[3], hashes, clave=CLAVE) is None
    assert buscar_respaldo("", hashes, clave=CLAVE) is None


@pytest.mark.parametrize(
    ("rol", "staff", "superusuario", "esperado"),
    [
        ("reportante", False, False, False),
        ("moderador", False, False, True),
        ("administrador", False, False, True),
        ("editor_catalogo", False, False, True),
        ("reportante", True, False, True),
        ("reportante", False, True, True),
    ],
)
def test_es_obligatoria_para_moderacion_y_administracion(rol, staff, superusuario, esperado):
    obligatorio = segundo_factor_obligatorio(rol=rol, es_staff=staff, es_superusuario=superusuario)
    assert obligatorio is esperado


@pytest.mark.parametrize(
    ("obligatorio", "activado", "confianza", "esperado"),
    [
        (False, False, False, False),
        (False, True, False, True),
        (True, False, False, True),
        (True, True, True, False),  # dispositivo de confianza durante 30 días
    ],
)
def test_cuando_se_pide_el_segundo_paso(obligatorio, activado, confianza, esperado):
    pedir = pedir_segundo_factor(
        obligatorio=obligatorio, activado=activado, dispositivo_de_confianza=confianza
    )
    assert pedir is esperado
