"""Ajustes que dependen de la plataforma de despliegue (ADR-0031). Python puro: lo usa settings.

Render (ADR-017) corre un proceso permanente y reutiliza conexiones (CONN_MAX_AGE); nada cambia
ahí. Vercel ejecuta funciones efímeras: cada invocación abre y cierra su conexión, siempre con TLS,
y los dominios *.vercel.app se aceptan solo si se declaran uno a uno.
"""

import re
from collections.abc import Iterable, Mapping

SSLMODES_ESTRICTOS = frozenset({"require", "verify-ca", "verify-full"})
_FALSOS = frozenset({"", "0", "false", "no"})
# Una sola etiqueta antes de .vercel.app: sin comodines, puntos iniciales ni subdominios extra
_DOMINIO_VERCEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.vercel\.app$")


def es_vercel(entorno: Mapping[str, str]) -> bool:
    """Vercel define VERCEL=1 en la construcción y en la ejecución."""
    return (entorno.get("VERCEL") or "").strip().lower() not in _FALSOS


def ajustar_bd_serverless(config: Mapping, *, en_vercel: bool) -> dict:
    """En Vercel: sin conexiones persistentes, sin cursores de servidor y con sslmode≥require.

    El pooler (PgBouncer de Neon, modo transacción) es quien reutiliza conexiones; una conexión
    persistente en una función congelada solo agota el cupo del servidor.
    """
    if not en_vercel:
        return dict(config)
    ajustada = {**config, "CONN_MAX_AGE": 0, "DISABLE_SERVER_SIDE_CURSORS": True}
    opciones = dict(config.get("OPTIONS", {}))
    if "postgresql" in config.get("ENGINE", "") and opciones.get("sslmode") not in (
        SSLMODES_ESTRICTOS
    ):
        opciones["sslmode"] = "require"
    ajustada["OPTIONS"] = opciones
    return ajustada


def validar_dominios_vercel(dominios: Iterable[str]) -> list[str]:
    """Dominios exactos «proyecto.vercel.app». Un comodín aceptaría cualquier proyecto ajeno."""
    validos: list[str] = []
    for crudo in dominios:
        dominio = crudo.strip().lower()
        if not dominio:
            continue
        if not _DOMINIO_VERCEL.fullmatch(dominio):
            raise ValueError(
                f"DOMINIOS_VERCEL: «{crudo}» no es un dominio exacto <proyecto>.vercel.app "
                "(sin comodines, esquema ni barra final; los dominios propios van en ALLOWED_HOSTS)"
            )
        if dominio not in validos:
            validos.append(dominio)
    return validos
