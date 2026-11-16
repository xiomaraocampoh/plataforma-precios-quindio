"""Cálculo de M-01, M-02, M-04 y SUS de la prueba de usabilidad (PUX-01, EC-01)."""

from decimal import Decimal
from pathlib import Path

import pytest

from scripts.calcular_usabilidad import (
    calcular,
    leer_registro,
    leer_sus,
    m01_registro_rapido,
    m02_registros_con_error,
    m04_sin_ayuda,
    main,
    puntaje_sus,
)

pytestmark = pytest.mark.unit

CABECERA = "participante,tarea,tiempo_s,completo,error,pidio_ayuda,observaciones\n"
CABECERA_SUS = "participante,p1,p2,p3,p4,p5,p6,p7,p8,p9,p10\n"
PLANTILLAS = Path("docs/calidad/usabilidad")


def registro(*filas: str):
    return leer_registro((CABECERA + "\n".join(filas)).splitlines())


def test_m01_cuenta_registros_completados_en_15_s_o_menos_sobre_intentos():
    # M-01: el límite de 15 s es inclusivo; un intento no completado cuenta como intento
    intentos = registro(
        "P1,T2,12.5,s,ninguno,n,",
        "P2,T2,15,s,ninguno,n,",
        "P3,T2,15.1,s,ninguno,n,",
        "P4,T2,,n,,s,abandonó",
        "P1,T1,40,s,,n,",  # otras tareas no cuentan para M-01
    )
    assert m01_registro_rapido(intentos) == Decimal("50.0")


def test_m02_cuenta_registros_completados_con_algun_error():
    # M-02: solo los registros completados; varios errores en una fila cuentan una vez
    intentos = registro(
        "P1,T2,10,s,ninguno,n,",
        "P2,T2,11,s,unidad,n,",
        "P3,T2,12,s,presentacion;establecimiento,n,",
        "P4,T2,13,s,,n,",
        "P5,T2,,n,unidad,n,",  # no completado: fuera del denominador
    )
    assert m02_registros_con_error(intentos) == Decimal("50.0")


def test_m04_cuenta_participantes_que_completan_todo_sin_ayuda():
    intentos = registro(
        "P1,T1,20,s,,n,",
        "P1,T2,10,s,ninguno,n,",
        "P2,T1,25,s,,n,",
        "P2,T2,18,s,ninguno,s,necesitó pista",  # pidió ayuda
        "P3,T1,30,s,,n,",
        "P3,T2,,n,,n,",  # no completó
    )
    assert m04_sin_ayuda(intentos) == Decimal("33.3")


def test_puntaje_sus_aplica_la_formula_de_brooke():
    assert puntaje_sus([4, 2, 4, 1, 4, 2, 5, 2, 4, 2]) == Decimal("80.0")
    assert puntaje_sus([5, 1, 5, 1, 5, 1, 5, 1, 5, 1]) == Decimal("100.0")
    assert puntaje_sus([1, 5, 1, 5, 1, 5, 1, 5, 1, 5]) == Decimal("0.0")
    assert puntaje_sus([3] * 10) == Decimal("50.0")


@pytest.mark.parametrize("respuestas", [[3] * 9, [3] * 9 + [6], [0] + [3] * 9])
def test_puntaje_sus_rechaza_respuestas_incompletas_o_fuera_de_escala(respuestas):
    with pytest.raises(ValueError):
        puntaje_sus(respuestas)


def test_las_filas_sin_datos_de_la_plantilla_se_ignoran():
    intentos = registro("P1,T1,,,,,", "P1,T2,,,,,")
    assert intentos == []
    assert m01_registro_rapido(intentos) is None
    assert m02_registros_con_error(intentos) is None
    assert m04_sin_ayuda(intentos) is None


@pytest.mark.parametrize(
    "fila",
    [
        "P1,T2,10,quizás,ninguno,n,",  # completo no es s/n
        "P1,T2,diez,s,ninguno,n,",  # tiempo no numérico
        "P1,T2,-3,s,ninguno,n,",  # tiempo negativo
        "P1,T2,10,s,color,n,",  # tipo de error desconocido
        "P1,T9,10,s,ninguno,n,",  # tarea inexistente
    ],
)
def test_valores_invalidos_se_rechazan_indicando_la_linea(fila):
    with pytest.raises(ValueError, match="línea 2"):
        registro(fila)


def test_leer_sus_devuelve_un_puntaje_por_participante_y_omite_vacios():
    lineas = (CABECERA_SUS + "P1,4,2,4,1,4,2,5,2,4,2\nP2,,,,,,,,,,\n").splitlines()
    assert leer_sus(lineas) == {"P1": Decimal("80.0")}


def test_las_plantillas_del_kit_no_traen_resultados():
    # El kit se entrega vacío: ningún resultado inventado
    with (PLANTILLAS / "registro.csv").open(encoding="utf-8") as f:
        assert leer_registro(f) == []
    with (PLANTILLAS / "sus.csv").open(encoding="utf-8") as f:
        assert leer_sus(f) == {}


def test_calcular_resume_metricas_y_umbrales():
    intentos = registro("P1,T1,20,s,,n,", "P1,T2,10,s,ninguno,n,")
    resultado = calcular(intentos, {"P1": Decimal("80.0")})
    assert resultado["M-01"].valor == Decimal("100.0")
    assert resultado["M-01"].cumple_minimo is True
    assert resultado["M-02"].valor == Decimal("0.0")
    assert resultado["M-02"].cumple_minimo is True
    assert resultado["SUS"].valor == Decimal("80.0")


def test_main_con_las_plantillas_vacias_informa_sin_datos(capsys):
    codigo = main([str(PLANTILLAS / "registro.csv"), str(PLANTILLAS / "sus.csv")])
    salida = capsys.readouterr().out
    assert codigo == 0
    assert "sin datos" in salida
    assert "Participantes evaluados: 0" in salida
