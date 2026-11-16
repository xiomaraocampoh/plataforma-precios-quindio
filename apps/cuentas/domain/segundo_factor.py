"""Verificación en dos pasos (RF-27). Python puro.

Códigos de 6 dígitos que vencen a los 10 minutos, máximo 5 intentos fallidos y luego 15 minutos de
bloqueo. De cada código solo se guarda un HMAC-SHA256: si la base se filtra, los códigos no.
"""

import hashlib
import hmac
import secrets
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import StrEnum

DIGITOS = 6
VIGENCIA_CODIGO = timedelta(minutes=10)
MAX_INTENTOS = 5
BLOQUEO = timedelta(minutes=15)
N_RESPALDO = 10
_ALFABETO_RESPALDO = "23456789abcdefghjkmnpqrstuvwxyz"  # sin 0/o ni 1/l/i: se dictan sin error
ROLES_CON_2FA_OBLIGATORIA = frozenset({"moderador", "administrador", "editor_catalogo"})


class Resultado(StrEnum):
    VALIDO = "valido"
    INCORRECTO = "incorrecto"
    VENCIDO = "vencido"
    BLOQUEADO = "bloqueado"


@dataclass(frozen=True)
class EstadoIntentos:
    intentos_fallidos: int = 0
    bloqueado_hasta: datetime | None = None


def generar_codigo(aleatorio: Callable[[int], int] = secrets.randbelow) -> str:
    return f"{aleatorio(10**DIGITOS):0{DIGITOS}d}"


def _normalizar(codigo: str) -> str:
    return "".join(codigo.split()).replace("-", "").lower()


def hash_codigo(codigo: str, *, clave: str) -> str:
    return hmac.new(clave.encode(), _normalizar(codigo).encode(), hashlib.sha256).hexdigest()


def coincide(codigo: str, hash_guardado: str, *, clave: str) -> bool:
    if not codigo or not hash_guardado:
        return False
    return hmac.compare_digest(hash_codigo(codigo, clave=clave), hash_guardado)


def evaluar(
    *,
    es_correcto: Callable[[], bool],
    estado: EstadoIntentos,
    ahora: datetime,
    vence_en: datetime | None,
) -> tuple[Resultado, EstadoIntentos]:
    """Aplica la política de intentos. `es_correcto` no se llama si la cuenta está bloqueada."""
    if estado.bloqueado_hasta and ahora < estado.bloqueado_hasta:
        return Resultado.BLOQUEADO, estado
    if vence_en is not None and ahora > vence_en:
        return Resultado.VENCIDO, estado
    if es_correcto():
        return Resultado.VALIDO, EstadoIntentos()
    fallidos = estado.intentos_fallidos + 1
    if fallidos >= MAX_INTENTOS:
        return Resultado.BLOQUEADO, EstadoIntentos(bloqueado_hasta=ahora + BLOQUEO)
    return Resultado.INCORRECTO, replace(estado, intentos_fallidos=fallidos, bloqueado_hasta=None)


def generar_codigos_respaldo(n: int = N_RESPALDO) -> list[str]:
    codigos: set[str] = set()
    while len(codigos) < n:
        texto = "".join(secrets.choice(_ALFABETO_RESPALDO) for _ in range(8))
        codigos.add(f"{texto[:4]}-{texto[4:]}")
    return sorted(codigos)


def buscar_respaldo(codigo: str, hashes: Sequence[str], *, clave: str) -> int | None:
    """Posición del código de respaldo sin usar que coincide (los usados tienen hash vacío)."""
    for posicion, guardado in enumerate(hashes):
        if coincide(codigo, guardado, clave=clave):
            return posicion
    return None


def segundo_factor_obligatorio(*, rol: str, es_staff: bool, es_superusuario: bool) -> bool:
    return es_staff or es_superusuario or rol in ROLES_CON_2FA_OBLIGATORIA


def pedir_segundo_factor(
    *, obligatorio: bool, activado: bool, dispositivo_de_confianza: bool
) -> bool:
    return (obligatorio or activado) and not dispositivo_de_confianza
