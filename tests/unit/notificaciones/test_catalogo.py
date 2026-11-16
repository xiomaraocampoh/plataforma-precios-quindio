"""Catálogo de correos, preferencias (Ley 1581), reintentos y privacidad en los logs."""

from datetime import UTC, datetime, timedelta

import pytest

from apps.notificaciones.domain.catalogo import (
    Categoria,
    Tipo,
    categoria_de,
    contexto_persistible,
    debe_enviarse,
)
from apps.notificaciones.domain.privacidad import enmascarar_correo
from apps.notificaciones.domain.reintentos import MAX_INTENTOS, espera_tras, puede_reintentar

pytestmark = pytest.mark.unit

AHORA = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
SEGURIDAD = {
    Tipo.VERIFICAR_CORREO,
    Tipo.RECUPERAR_CONTRASENA,
    Tipo.CONTRASENA_CAMBIADA,
    Tipo.NUEVO_DISPOSITIVO,
    Tipo.CODIGO_VERIFICACION,
    Tipo.CUENTA_SUSPENDIDA,
    Tipo.CUENTA_SUPRIMIDA,
}


def _debe(tipo, *, tiene=True, verificado=True, acepta=True):
    return debe_enviarse(
        tipo=tipo, tiene_correo=tiene, correo_verificado=verificado, acepta_informativos=acepta
    )


def test_cada_tipo_tiene_su_categoria():
    for tipo in Tipo:
        esperado = Categoria.SEGURIDAD if tipo in SEGURIDAD else Categoria.INFORMATIVO
        assert categoria_de(tipo) == esperado
    informativos = {t for t in Tipo if t not in SEGURIDAD}
    assert {Tipo.BIENVENIDA, Tipo.REPORTE_MODERADO, Tipo.DENUNCIA_RESUELTA} <= informativos


@pytest.mark.parametrize("tipo", sorted(SEGURIDAD))
def test_los_de_seguridad_son_obligatorios(tipo):
    assert _debe(tipo, verificado=False, acepta=False)


def test_los_informativos_respetan_la_preferencia_y_exigen_correo_verificado():
    assert _debe(Tipo.REPORTE_MODERADO)
    assert not _debe(Tipo.REPORTE_MODERADO, acepta=False)
    assert not _debe(Tipo.REPORTE_MODERADO, verificado=False)


def test_sin_correo_no_se_envia_nada():
    assert not _debe(Tipo.CODIGO_VERIFICACION, tiene=False)


def test_el_contexto_guardado_nunca_lleva_secretos():
    contexto = {"nombre": "Ana", "codigo": "123456", "enlace": "https://x/t/a", "token": "t"}
    assert contexto_persistible({**contexto, "clave": "c", "contrasena": "x"}) == {"nombre": "Ana"}


def test_maximo_tres_intentos_con_espera_creciente():
    assert MAX_INTENTOS == 3
    assert espera_tras(1) < espera_tras(2) < espera_tras(3)
    assert puede_reintentar(intentos=0, ultimo_intento=None, ahora=AHORA)
    antes = AHORA + espera_tras(1) - timedelta(seconds=1)
    assert not puede_reintentar(intentos=1, ultimo_intento=AHORA, ahora=antes)
    assert puede_reintentar(intentos=1, ultimo_intento=AHORA, ahora=AHORA + espera_tras(1))
    manana = AHORA + timedelta(days=1)
    assert not puede_reintentar(intentos=3, ultimo_intento=AHORA, ahora=manana)


@pytest.mark.parametrize(
    ("correo", "esperado"),
    [
        ("lucia@example.com", "l***@e***.com"),
        ("a@b.co", "a***@b***.co"),
        ("", "(sin correo)"),
        ("raro", "***"),
    ],
)
def test_los_logs_solo_ven_el_correo_enmascarado(correo, esperado):
    assert enmascarar_correo(correo) == esperado
