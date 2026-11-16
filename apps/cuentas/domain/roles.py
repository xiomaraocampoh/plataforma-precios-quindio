"""Roles de la plataforma y sus permisos. Python puro: Django los aplica como Groups.

`Usuario.rol` es la fuente de verdad; el grupo de Django se sincroniza con él. Los permisos se
escriben como "app_label.codename", igual que `user.has_perm`.
"""

from enum import StrEnum


class Rol(StrEnum):
    ADMINISTRADOR = "administrador"
    MODERADOR = "moderador"
    EDITOR_CATALOGO = "editor_catalogo"
    REPORTANTE = "reportante"


# El rol «comercio» no tiene grupo: el módulo comercial se construye en el Corte III (EC-05)
GRUPOS: dict[Rol, str] = {
    Rol.ADMINISTRADOR: "Administrador",
    Rol.MODERADOR: "Moderador",
    Rol.EDITOR_CATALOGO: "Editor de catálogo",
    Rol.REPORTANTE: "Reportante",
}


def _crud(app: str, *modelos: str) -> frozenset[str]:
    return frozenset(f"{app}.{a}_{m}" for m in modelos for a in ("add", "change", "delete", "view"))


_CATALOGO = _crud("catalogo", "marca", "categoria", "producto", "presentacion") | {
    "catalogo.view_solicitudcatalogo"
}
_ESTABLECIMIENTOS = _crud("establecimientos", "establecimiento")
# Lo que moderación ya usaba en /admin/ (RF-21, RF-22)
_MODERACION = frozenset(
    {
        "precios.view_reporteprecio",
        "precios.change_reporteprecio",
        "moderacion.view_denuncia",
        "moderacion.change_denuncia",
        "moderacion.view_decisionmoderacion",
        "establecimientos.view_establecimiento",
        "establecimientos.change_establecimiento",
        "catalogo.view_solicitudcatalogo",
        "catalogo.change_solicitudcatalogo",
        "catalogo.view_producto",
        "catalogo.view_presentacion",
        "cuentas.view_usuario",
        "cuentas.change_usuario",
    }
)

PERMISOS: dict[Rol, frozenset[str]] = {
    Rol.REPORTANTE: frozenset(
        {
            "precios.add_reporteprecio",
            "precios.add_confirmacionprecio",
            "moderacion.add_denuncia",
            "catalogo.add_solicitudcatalogo",
        }
    ),
    Rol.EDITOR_CATALOGO: _CATALOGO,
    Rol.MODERADOR: _MODERACION,
    Rol.ADMINISTRADOR: _CATALOGO
    | _ESTABLECIMIENTOS
    | _MODERACION
    | {"cuentas.gestionar_cuentas", "administracion.view_registroauditoria"},
}


def grupo_de(rol: str) -> str | None:
    """Nombre del grupo de Django para el rol, o None si el rol no tiene grupo."""
    try:
        return GRUPOS[Rol(rol)]
    except ValueError:
        return None


class CambioDeCuentaNoPermitidoError(ValueError):
    """El cambio de rol o de estado de la cuenta no está permitido para quien lo intenta."""


def validar_cambio_de_cuenta(
    *, actor_id: int, objetivo_id: int, actor_es_superusuario: bool, objetivo_es_superusuario: bool
) -> None:
    if actor_id == objetivo_id:
        raise CambioDeCuentaNoPermitidoError(
            "No puedes cambiar tu propio rol ni el estado de tu propia cuenta."
        )
    if objetivo_es_superusuario and not actor_es_superusuario:
        raise CambioDeCuentaNoPermitidoError(
            "Solo un superusuario puede cambiar la cuenta de otro superusuario."
        )
