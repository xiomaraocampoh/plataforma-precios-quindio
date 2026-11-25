"""Qué correos existen, de qué categoría es cada uno y cuándo se envían (RF-24 a RF-27).

- Seguridad: obligatorios, llegan aunque el correo aún no esté verificado (la verificación misma
  es uno de ellos).
- Informativos: solo a un correo verificado y si la persona no los apagó (Ley 1581 de 2012).
"""

from collections.abc import Mapping
from enum import StrEnum


class Categoria(StrEnum):
    SEGURIDAD = "seguridad"
    INFORMATIVO = "informativo"


class Tipo(StrEnum):
    VERIFICAR_CORREO = "verificar_correo"
    RECUPERAR_CONTRASENA = "recuperar_contrasena"
    CONTRASENA_CAMBIADA = "contrasena_cambiada"
    NUEVO_DISPOSITIVO = "nuevo_dispositivo"
    CODIGO_VERIFICACION = "codigo_verificacion"
    CUENTA_SUSPENDIDA = "cuenta_suspendida"
    CUENTA_SUPRIMIDA = "cuenta_suprimida"
    BIENVENIDA = "bienvenida"
    DENUNCIA_RESUELTA = "denuncia_resuelta"
    REPORTE_MODERADO = "reporte_moderado"
    SOLICITUD_RESUELTA = "solicitud_resuelta"
    ESTABLECIMIENTO_RESUELTO = "establecimiento_resuelto"
    # Módulo comercial (Corte III): informativos, como las demás decisiones de moderación
    PERFIL_VERIFICADO = "perfil_verificado"
    CORRECCION_RESUELTA = "correccion_resuelta"


_SEGURIDAD = frozenset(
    {
        Tipo.VERIFICAR_CORREO,
        Tipo.RECUPERAR_CONTRASENA,
        Tipo.CONTRASENA_CAMBIADA,
        Tipo.NUEVO_DISPOSITIVO,
        Tipo.CODIGO_VERIFICACION,
        Tipo.CUENTA_SUSPENDIDA,
        Tipo.CUENTA_SUPRIMIDA,
    }
)

# Nunca se guardan en la cola: viajan solo en memoria para el primer intento (o se regeneran)
CLAVES_SENSIBLES = frozenset({"codigo", "enlace", "token", "clave", "contrasena", "password"})


def categoria_de(tipo: str) -> Categoria:
    return Categoria.SEGURIDAD if Tipo(tipo) in _SEGURIDAD else Categoria.INFORMATIVO


def debe_enviarse(
    *, tipo: str, tiene_correo: bool, correo_verificado: bool, acepta_informativos: bool
) -> bool:
    if not tiene_correo:
        return False
    if categoria_de(tipo) == Categoria.SEGURIDAD:
        return True
    return correo_verificado and acepta_informativos


def contexto_persistible(contexto: Mapping) -> dict:
    return {k: v for k, v in contexto.items() if k not in CLAVES_SENSIBLES}
