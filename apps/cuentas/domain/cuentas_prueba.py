"""Cuentas de prueba para probar cada rol en local. Python puro — TDD.

Las contraseñas NUNCA viven aquí: salen de la variable de entorno CUENTAS_PRUEBA_PASSWORD. Si no
existe, el comando se detiene; no se genera ni se imprime ninguna contraseña.
Los correos usan example.com (RFC 2606): nunca llegan a una persona real.
"""

from dataclasses import dataclass

VARIABLE_CONTRASENA = "CUENTAS_PRUEBA_PASSWORD"  # noqa: S105 — nombre de la variable, no clave


class ContrasenaDePruebaAusenteError(ValueError):
    """Falta la variable de entorno con la contraseña de las cuentas de prueba."""


@dataclass(frozen=True)
class CuentaPrueba:
    usuario: str
    rol: str
    correo: str
    puede_probar: str
    staff: bool = False
    superusuario: bool = False
    activa: bool = True


CUENTAS_PRUEBA: tuple[CuentaPrueba, ...] = (
    CuentaPrueba(
        "admin_prueba",
        "administrador",
        "admin+administrador@example.com",
        "Todo: /panel/ (catálogo, directorio, roles, auditoría), /admin/ y moderación.",
        staff=True,
        superusuario=True,
    ),
    CuentaPrueba(
        "moderador_prueba",
        "moderador",
        "moderador+moderador@example.com",
        "Cola de moderación: reportes en revisión, denuncias, solicitudes y sugerencias.",
        staff=True,
    ),
    CuentaPrueba(
        "editor_prueba",
        "editor_catalogo",
        "editor+editor_catalogo@example.com",
        "Panel de catálogo: marcas, categorías, productos y presentaciones.",
    ),
    CuentaPrueba(
        "reportante_prueba",
        "reportante",
        "prueba+reportante@example.com",
        "Registrar precios, «Sigue igual», denunciar, pedir productos y sugerir tiendas.",
    ),
    CuentaPrueba(
        "reportante_ana",
        "reportante",
        "ana+reportante@example.com",
        "Segunda persona: confirmar con «Sigue igual» precios de otra cuenta.",
    ),
    CuentaPrueba(
        "reportante_luis",
        "reportante",
        "luis+reportante@example.com",
        "Tercera persona: confianza alta (varios reportes iguales) y denuncias.",
    ),
    CuentaPrueba(
        "comercio_prueba",
        "comercio",
        "comercio+comercio@example.com",
        "Portal /comercios/: «Tienda Doña Gloria» verificada, con precios oficiales y promociones.",
    ),
    CuentaPrueba(
        "suspendido_prueba",
        "reportante",
        "suspendido+reportante@example.com",
        "Cuenta suspendida: el ingreso se rechaza (bloqueo de RF-22).",
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
