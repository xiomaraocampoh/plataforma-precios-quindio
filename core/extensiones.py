"""Registro de extensiones (ADR-012, DP-1 opción B).

Un módulo que extiende a otro se registra aquí al arrancar (`AppConfig.ready()`), con el nombre del
punto que el módulo extendido define en su dominio. Este registro no conoce a nadie: no importa
ningún módulo de negocio, así que el núcleo puede consultar extensiones sin depender de ellas
(contrato `comercios-no-adelantado`).

Python puro, sin Django: se prueba en tests/unit/test_registro_extensiones.py.
"""

from collections import defaultdict

_registro: dict[str, list[object]] = defaultdict(list)


def _punto_valido(punto: str) -> str:
    if not punto or not punto.strip():
        raise ValueError("El punto de extensión necesita un nombre.")
    return punto.strip()


def registrar(punto: str, extension: object) -> None:
    """Agrega la extensión al punto. Registrar dos veces la misma no la duplica."""
    lista = _registro[_punto_valido(punto)]
    if not any(e is extension for e in lista):
        lista.append(extension)


def retirar(punto: str, extension: object) -> None:
    """Quita la extensión del punto, si estaba (pruebas y apagado de un módulo)."""
    lista = _registro.get(punto.strip(), [])
    lista[:] = [e for e in lista if e is not extension]


def extensiones(punto: str) -> tuple[object, ...]:
    """Las extensiones del punto, en orden de registro (una copia inmutable)."""
    return tuple(_registro.get(punto.strip(), ()))
