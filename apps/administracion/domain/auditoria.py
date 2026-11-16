"""Qué cambió en una acción del panel, listo para guardarse en JSON (M-14).

La bitácora registra la acción y los datos del catálogo o del rol, nunca los datos personales del
titular (Ley 1581 de 2012).
"""

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

CAMPOS_PRIVADOS = frozenset({"password", "email", "first_name", "last_name"})


def valor_auditable(valor: Any) -> Any:
    """Valor serializable en JSON. Los decimales van como texto para no perder precisión."""
    if valor is None or isinstance(valor, bool | int | str):
        return valor
    if isinstance(valor, Decimal):
        return format(valor.normalize(), "f")
    if isinstance(valor, list | tuple):
        return [valor_auditable(v) for v in valor]
    return str(valor)


def diferencias(antes: Mapping[str, Any], despues: Mapping[str, Any]) -> dict[str, list]:
    """{campo: [antes, después]} de los campos que cambiaron; lo que falta cuenta como None."""
    campos = (antes.keys() | despues.keys()) - CAMPOS_PRIVADOS
    cambios = {}
    for campo in sorted(campos):
        a = valor_auditable(antes.get(campo))
        d = valor_auditable(despues.get(campo))
        if a != d:
            cambios[campo] = [a, d]
    return cambios
