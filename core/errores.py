"""Errores de aplicación compartidos por los módulos."""


class EnUsoError(Exception):
    """No se puede eliminar: tiene reportes u otros registros asociados. Se desactiva."""
