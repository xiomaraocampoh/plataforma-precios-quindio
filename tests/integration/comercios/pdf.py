"""PDF de prueba para la solicitud de perfil de comercio (ADR-0034)."""

from django.core.files.uploadedfile import SimpleUploadedFile

CAMARA = b"%PDF-1.7\n% certificado de camara de comercio de prueba\n%%EOF\n"
RUT = b"%PDF-1.4\n% rut de prueba\n%%EOF\n"


def archivo(nombre: str, contenido: bytes, tipo: str = "application/pdf") -> SimpleUploadedFile:
    return SimpleUploadedFile(nombre, contenido, content_type=tipo)


def pdfs(**cambios) -> dict:
    """Los dos documentos válidos; `cambios` reemplaza uno (o lo quita con None)."""
    documentos = {
        "camara_comercio": archivo("Certificado Camara.pdf", CAMARA),
        "rut": archivo("RUT-DIAN.PDF", RUT),
    }
    documentos.update(cambios)
    return documentos
