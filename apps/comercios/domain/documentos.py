"""Evidencia de un comercio en PDF (ADR-0034, RF-C02): qué archivo se acepta.

Capa de dominio: Python puro, sin Django. El formulario usa esta regla para mostrar el error en el
campo, y el servicio la repite antes de guardar.

- Extensión `.pdf`, sin importar mayúsculas («RUT.PDF» sirve; «rut.pdf.exe» no).
- Cabecera `%PDF-`: un PNG renombrado a `.pdf` no pasa.
- Entre 1 byte y 2 MB: van dos archivos por petición y Vercel corta en 4,5 MB (ADR-0031).
"""

MAX_BYTES_DOCUMENTO = 2 * 1024 * 1024
CABECERA_PDF = b"%PDF-"
_EXTENSION = ".pdf"


class DocumentoInvalidoError(ValueError):
    """El archivo no sirve como evidencia. El mensaje es una oración lista para mostrar."""


def _tiene_extension_pdf(nombre: str) -> bool:
    limpio = nombre.strip().lower()
    return limpio.endswith(_EXTENSION) and len(limpio) > len(_EXTENSION)


def validar_pdf(nombre: str, tamano: int, cabecera: bytes) -> None:
    """Lanza DocumentoInvalidoError si el archivo no es un PDF aceptable; si no, no devuelve nada.

    `cabecera` son los primeros bytes del archivo (basta con 5).
    """
    if not _tiene_extension_pdf(nombre):
        raise DocumentoInvalidoError("El archivo debe ser un PDF (.pdf).")
    if tamano <= 0:
        raise DocumentoInvalidoError("El archivo está vacío.")
    if tamano > MAX_BYTES_DOCUMENTO:
        megas = MAX_BYTES_DOCUMENTO // (1024 * 1024)
        raise DocumentoInvalidoError(f"El archivo pesa más de {megas} MB.")
    if not cabecera.startswith(CABECERA_PDF):
        raise DocumentoInvalidoError("El archivo no es un PDF válido.")
