"""Cuentas de prueba para probar cada rol en local. Python puro — TDD.

Las contraseñas NUNCA viven aquí: salen de la variable de entorno CUENTAS_PRUEBA_PASSWORD. Si no
existe, el comando se detiene; no se genera ni se imprime ninguna contraseña.
Correos: por defecto, example.com (RFC 2606), que nunca llega a una persona real. Si se define
CUENTAS_PRUEBA_CORREO_BASE (un buzón del equipo), cada cuenta usa «parte_local+sufijo@dominio» para
que el código del 2FA llegue a ese buzón (en producción el 2FA no se puede omitir).
"""

from dataclasses import dataclass, field

VARIABLE_CONTRASENA = "CUENTAS_PRUEBA_PASSWORD"  # noqa: S105 — nombre de la variable, no clave
VARIABLE_CORREO_BASE = "CUENTAS_PRUEBA_CORREO_BASE"


class ContrasenaDePruebaAusenteError(ValueError):
    """Falta la variable de entorno con la contraseña de las cuentas de prueba."""


class CorreoBaseInvalidoError(ValueError):
    """CUENTAS_PRUEBA_CORREO_BASE no tiene la forma parte_local@dominio."""


@dataclass(frozen=True)
class CuentaPrueba:
    usuario: str
    rol: str
    correo: str
    puede_probar: str
    sufijo: str = field(kw_only=True)  # va tras el «+» cuando hay CUENTAS_PRUEBA_CORREO_BASE
    staff: bool = False
    superusuario: bool = False
    activa: bool = True


CUENTAS_PRUEBA: tuple[CuentaPrueba, ...] = (
    CuentaPrueba(
        "admin_prueba",
        "administrador",
        "admin+administrador@example.com",
        "Todo: /panel/ (catálogo, directorio, roles, auditoría), /admin/ y moderación.",
        sufijo="admin",
        staff=True,
        superusuario=True,
    ),
    CuentaPrueba(
        "moderador_prueba",
        "moderador",
        "moderador+moderador@example.com",
        "Cola de moderación: reportes en revisión, denuncias, solicitudes y sugerencias.",
        sufijo="moderador",
        staff=True,
    ),
    CuentaPrueba(
        "editor_prueba",
        "editor_catalogo",
        "editor+editor_catalogo@example.com",
        "Panel de catálogo: marcas, categorías, productos y presentaciones.",
        sufijo="editor",
    ),
    CuentaPrueba(
        "reportante_prueba",
        "reportante",
        "prueba+reportante@example.com",
        "Registrar precios, «Sigue igual», denunciar, pedir productos y sugerir tiendas.",
        sufijo="reportante",
    ),
    CuentaPrueba(
        "reportante_ana",
        "reportante",
        "ana+reportante@example.com",
        "Segunda persona: confirmar con «Sigue igual» precios de otra cuenta.",
        sufijo="ana",
    ),
    CuentaPrueba(
        "reportante_luis",
        "reportante",
        "luis+reportante@example.com",
        "Tercera persona: confianza alta (varios reportes iguales) y denuncias.",
        sufijo="luis",
    ),
    CuentaPrueba(
        "comercio_prueba",
        "comercio",
        "comercio+comercio@example.com",
        "Portal /comercios/: «Tienda Doña Gloria» verificada, con precios oficiales y promociones.",
        sufijo="comercio",
    ),
    CuentaPrueba(
        "suspendido_prueba",
        "reportante",
        "suspendido+reportante@example.com",
        "Cuenta suspendida: el ingreso se rechaza (bloqueo de RF-22).",
        sufijo="suspendido",
        activa=False,
    ),
)


def exigir_contrasena_de_prueba(valor: str | None) -> str:
    """Devuelve la contraseña de la variable de entorno o se detiene si falta."""
    if not valor or not valor.strip():
        raise ContrasenaDePruebaAusenteError(
            f"Defina la variable de entorno {VARIABLE_CONTRASENA} con la contraseña de las "
            "cuentas de prueba. El comando no genera ni muestra contraseñas."
        )
    return valor


def _partes_de_la_base(base: str) -> tuple[str, str]:
    local, arroba, dominio = base.partition("@")
    valida = (
        arroba
        and local
        and "." in dominio.strip(".")
        and not any(c.isspace() or c in "@+" for c in local + dominio)
    )
    if not valida:
        raise CorreoBaseInvalidoError(
            f"{VARIABLE_CORREO_BASE} debe ser un correo con la forma parte_local@dominio, sin "
            "espacios ni «+» (cada cuenta le agrega +sufijo). Déjela vacía para usar example.com."
        )
    return local, dominio


def correo_de_prueba(cuenta: CuentaPrueba, correo_base: str | None) -> str:
    """El correo de la cuenta: «parte_local+sufijo@dominio» con base; el de example.com sin ella."""
    base = (correo_base or "").strip()
    if not base:
        return cuenta.correo
    local, dominio = _partes_de_la_base(base)
    return f"{local}+{cuenta.sufijo}@{dominio}"


def correos_de_prueba(correo_base: str | None) -> dict[str, str]:
    """El correo de cada cuenta de prueba, por nombre de usuario."""
    return {c.usuario: correo_de_prueba(c, correo_base) for c in CUENTAS_PRUEBA}
