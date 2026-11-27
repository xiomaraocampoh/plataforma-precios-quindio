"""Evidencia de un comercio en PDF (ADR-0034): qué archivo se acepta.

Capa de dominio: Python puro, sin Django.
"""

MAX_BYTES_DOCUMENTO = 2 * 1024 * 1024
CABECERA_PDF = b"%PDF-"


class DocumentoInvalidoError(ValueError):
    """El archivo no sirve como evidencia."""


def validar_pdf(nombre: str, tamano: int, cabecera: bytes) -> None:
    nombre = nombre.strip().lower()
    if not nombre or not nombre.endswith(".pdf") or nombre == ".pdf":
        raise DocumentoInvalidoError("El archivo debe ser un PDF (.pdf).")
    if tamano <= 0:
        raise DocumentoInvalidoError("El archivo está vacío.")
    if tamano > MAX_BYTES_DOCUMENTO:
        raise DocumentoInvalidoError("El archivo pesa más de 2 MB.")
    if not cabecera.startswith(CABECERA_PDF):
        raise DocumentoInvalidoError("El archivo no es un PDF válido.")
