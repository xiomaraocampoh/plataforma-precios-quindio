"""Enlace al panel en el menú de la cuenta, solo para quien tiene alguna sección visible."""

from .secciones import accesos


def panel(request):
    usuario = getattr(request, "user", None)
    # Perezoso: la plantilla lo evalúa solo si lo usa (no consulta permisos en cada página)
    return {"panel_disponible": lambda: bool(accesos(usuario))}
