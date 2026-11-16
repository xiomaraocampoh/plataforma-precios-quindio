"""Casos de uso de cuentas (capa de aplicación), separados por tema.

- basicos: registro, datos, roles, suspensión y supresión.
- correo: verificación del correo, recuperación y avisos de seguridad (RF-24, RF-25).
- segundo_factor: verificación en dos pasos (RF-27).
"""

from . import correo, segundo_factor
from .basicos import (
    actualizar_datos,
    asegurar_administrador,
    asegurar_grupo,
    asegurar_moderador,
    asignar_rol,
    cambiar_estado_cuenta,
    permisos_por_nombre,
    registrar_usuario,
    sincronizar_grupo_de_rol,
    suprimir_cuenta,
    suspender_cuenta,
)

__all__ = [
    "actualizar_datos",
    "asegurar_administrador",
    "asegurar_grupo",
    "asegurar_moderador",
    "asignar_rol",
    "cambiar_estado_cuenta",
    "correo",
    "permisos_por_nombre",
    "registrar_usuario",
    "segundo_factor",
    "sincronizar_grupo_de_rol",
    "suprimir_cuenta",
    "suspender_cuenta",
]
