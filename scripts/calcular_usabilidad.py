"""Calcula M-01, M-02, M-04 y el puntaje SUS de la prueba de usabilidad (PUX-01, EC-01).

Uso, desde la raíz del repositorio:
    python scripts/calcular_usabilidad.py docs/calidad/usabilidad/registro.csv \\
        docs/calidad/usabilidad/sus.csv

- M-01: registros de T2 completados en <= 15 s / intentos de T2.
- M-02: registros de T2 completados con unidad, presentación o establecimiento equivocado /
  registros de T2 completados.
- M-04: participantes que completan todas sus tareas sin pedir ayuda / participantes evaluados.
- SUS: promedio de los puntajes por participante (fórmula de Brooke, 0 a 100).

Las filas sin «completo» (plantilla vacía) se ignoran: el script nunca inventa datos.
"""

import csv
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

TAREAS = {"T1", "T2", "T3", "T4"}
TAREA_REGISTRO = "T2"
LIMITE_REGISTRO_S = Decimal("15")
TIPOS_DE_ERROR = {"unidad", "presentacion", "establecimiento"}
SIN_ERROR = {"", "ninguno"}
SI = {"s", "si", "sí"}
NO = {"n", "no"}
ITEMS_SUS = 10
ESCALA_SUS = range(1, 6)
FACTOR_SUS = Decimal("2.5")
UN_DECIMAL = Decimal("0.1")


@dataclass(frozen=True)
class Intento:
    participante: str
    tarea: str
    tiempo_s: Decimal | None
    completo: bool
    errores: frozenset[str]
    pidio_ayuda: bool


@dataclass(frozen=True)
class Metrica:
    nombre: str
    valor: Decimal | None
    minimo: Decimal
    objetivo: Decimal
    mayor_es_mejor: bool = True

    @property
    def cumple_minimo(self) -> bool | None:
        if self.valor is None:
            return None
        return self.valor >= self.minimo if self.mayor_es_mejor else self.valor <= self.minimo


def _redondear(valor: Decimal) -> Decimal:
    return valor.quantize(UN_DECIMAL, rounding=ROUND_HALF_UP)


def _porcentaje(parte: int, total: int) -> Decimal | None:
    return None if total == 0 else _redondear(Decimal(100) * parte / total)


def _si_no(valor: str, campo: str, linea: int) -> bool:
    texto = valor.strip().lower()
    if texto in SI:
        return True
    if texto in NO:
        return False
    raise ValueError(f"línea {linea}: «{campo}» debe ser s o n, no «{valor}».")


def _tiempo(valor: str, linea: int) -> Decimal | None:
    if not valor.strip():
        return None
    try:
        tiempo = Decimal(valor.strip())
    except InvalidOperation:
        raise ValueError(f"línea {linea}: tiempo_s no es un número: «{valor}».") from None
    if tiempo < 0:
        raise ValueError(f"línea {linea}: tiempo_s no puede ser negativo.")
    return tiempo


def _errores(valor: str, linea: int) -> frozenset[str]:
    tipos = {e.strip().lower() for e in valor.split(";")} - SIN_ERROR
    desconocidos = tipos - TIPOS_DE_ERROR
    if desconocidos:
        raise ValueError(
            f"línea {linea}: error desconocido {sorted(desconocidos)}; "
            f"usa {sorted(TIPOS_DE_ERROR)} o «ninguno»."
        )
    return frozenset(tipos)


def leer_registro(lineas: Iterable[str]) -> list[Intento]:
    """Lee registro.csv; omite las filas que todavía no tienen «completo»."""
    intentos = []
    for linea, fila in enumerate(csv.DictReader(lineas), start=2):
        if not (fila.get("completo") or "").strip():
            continue
        tarea = fila["tarea"].strip().upper()
        if tarea not in TAREAS:
            raise ValueError(f"línea {linea}: tarea «{tarea}» no existe ({sorted(TAREAS)}).")
        intentos.append(
            Intento(
                participante=fila["participante"].strip(),
                tarea=tarea,
                tiempo_s=_tiempo(fila.get("tiempo_s") or "", linea),
                completo=_si_no(fila["completo"], "completo", linea),
                errores=_errores(fila.get("error") or "", linea),
                pidio_ayuda=_si_no(fila.get("pidio_ayuda") or "n", "pidio_ayuda", linea),
            )
        )
    return intentos


def puntaje_sus(respuestas: list[int]) -> Decimal:
    """Puntaje SUS de un participante: 2,5 x suma(impares - 1) + suma(5 - pares)."""
    if len(respuestas) != ITEMS_SUS or any(r not in ESCALA_SUS for r in respuestas):
        raise ValueError("El SUS necesita 10 respuestas entre 1 y 5.")
    impares = sum(r - 1 for r in respuestas[0::2])
    pares = sum(5 - r for r in respuestas[1::2])
    return _redondear(FACTOR_SUS * (impares + pares))


def leer_sus(lineas: Iterable[str]) -> dict[str, Decimal]:
    """Lee sus.csv; omite participantes sin respuestas."""
    puntajes = {}
    for linea, fila in enumerate(csv.DictReader(lineas), start=2):
        valores = [(fila.get(f"p{i}") or "").strip() for i in range(1, ITEMS_SUS + 1)]
        if not any(valores):
            continue
        try:
            respuestas = [int(v) for v in valores]
        except ValueError:
            raise ValueError(f"línea {linea}: las respuestas SUS deben ser enteros.") from None
        puntajes[fila["participante"].strip()] = puntaje_sus(respuestas)
    return puntajes


def m01_registro_rapido(intentos: list[Intento]) -> Decimal | None:
    registros = [i for i in intentos if i.tarea == TAREA_REGISTRO]
    rapidos = [
        i
        for i in registros
        if i.completo and i.tiempo_s is not None and i.tiempo_s <= LIMITE_REGISTRO_S
    ]
    return _porcentaje(len(rapidos), len(registros))


def m02_registros_con_error(intentos: list[Intento]) -> Decimal | None:
    completados = [i for i in intentos if i.tarea == TAREA_REGISTRO and i.completo]
    return _porcentaje(sum(1 for i in completados if i.errores), len(completados))


def m04_sin_ayuda(intentos: list[Intento]) -> Decimal | None:
    por_participante: dict[str, list[Intento]] = {}
    for i in intentos:
        por_participante.setdefault(i.participante, []).append(i)
    autonomos = [
        p
        for p, suyos in por_participante.items()
        if all(i.completo and not i.pidio_ayuda for i in suyos)
    ]
    return _porcentaje(len(autonomos), len(por_participante))


def calcular(intentos: list[Intento], sus: dict[str, Decimal]) -> dict[str, Metrica]:
    promedio = _redondear(sum(sus.values()) / len(sus)) if sus else None
    return {
        "M-01": Metrica(
            "Registro en <= 15 s", m01_registro_rapido(intentos), Decimal(80), Decimal(90)
        ),
        "M-02": Metrica(
            "Registros con error", m02_registros_con_error(intentos), Decimal(10), Decimal(5), False
        ),
        "M-04": Metrica("Completan sin ayuda", m04_sin_ayuda(intentos), Decimal(80), Decimal(90)),
        "SUS": Metrica("Puntaje SUS promedio", promedio, Decimal(68), Decimal(80)),
    }


def _linea(clave: str, m: Metrica) -> str:
    unidad = "" if clave == "SUS" else " %"
    signo = ">=" if m.mayor_es_mejor else "<="  # ASCII: la consola de Windows usa cp1252
    umbral = f"mínimo {signo} {m.minimo}{unidad}, objetivo {signo} {m.objetivo}{unidad}"
    if m.valor is None:
        return f"{clave:5} {m.nombre:24} sin datos          ({umbral})"
    estado = "CUMPLE" if m.cumple_minimo else "NO CUMPLE"
    return f"{clave:5} {m.nombre:24} {m.valor:>6}{unidad:2} {estado:9} ({umbral})"


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:  # noqa: PLR2004 - dos rutas: registro y SUS
        print(__doc__)
        return 2
    with Path(args[0]).open(encoding="utf-8") as f:
        intentos = leer_registro(f)
    with Path(args[1]).open(encoding="utf-8") as f:
        sus = leer_sus(f)
    participantes = {i.participante for i in intentos}
    print("Prueba de usabilidad PUX-01 - EC-01")
    print(f"Participantes evaluados: {len(participantes)} - cuestionarios SUS: {len(sus)}")
    for clave, metrica in calcular(intentos, sus).items():
        print(_linea(clave, metrica))
    for participante, puntaje in sorted(sus.items()):
        print(f"  SUS {participante}: {puntaje}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
