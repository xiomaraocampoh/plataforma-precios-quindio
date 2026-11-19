"""Procesamiento de la foto de un producto con Pillow (ADR-0024).

Convierte lo que sube una persona en una miniatura WebP cuadrada de LADO_MINIATURA px. Lo que se
guarda es SIEMPRE una imagen nueva generada aquí: se descartan los metadatos (EXIF con la cámara
o la ubicación, Ley 1581) y cualquier contenido oculto en el archivo original.
Las reglas de qué se acepta viven en el dominio (`domain/fotos.py`, Python puro).
"""

from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

from .domain.fotos import LADO_MINIATURA, FotoInvalidaError, recorte_cuadrado, validar_subida

CALIDAD_WEBP = 80
_NO_ES_IMAGEN = "El archivo no es una imagen válida. Usa una foto JPG, PNG o WebP."


def _sobre_fondo_blanco(foto: Image.Image) -> Image.Image:
    """Las transparencias de un PNG se pasan a blanco: el WebP final no lleva canal alfa."""
    if foto.mode in ("RGBA", "LA", "P"):
        con_alfa = foto.convert("RGBA")
        fondo = Image.new("RGB", con_alfa.size, (255, 255, 255))
        fondo.paste(con_alfa, mask=con_alfa.getchannel("A"))
        return fondo
    return foto.convert("RGB")


def procesar(datos: bytes) -> bytes:
    """Bytes de una foto subida -> bytes de la miniatura WebP cuadrada. Lanza FotoInvalidaError."""
    try:
        with Image.open(BytesIO(datos)) as original:
            validar_subida(
                formato=original.format,
                ancho=original.width,
                alto=original.height,
                tamano=len(datos),
            )  # antes de decodificar: una imagen enorme no llega a ocupar memoria
            original.load()  # falla si el archivo está truncado o corrupto
            foto = ImageOps.exif_transpose(original)  # respeta la orientación de la cámara
            foto = _sobre_fondo_blanco(foto)
    except FotoInvalidaError:
        raise
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, Image.DecompressionBombError):
        raise FotoInvalidaError(_NO_ES_IMAGEN) from None
    foto = foto.crop(recorte_cuadrado(*foto.size)).resize(
        (LADO_MINIATURA, LADO_MINIATURA), Image.Resampling.LANCZOS
    )
    salida = BytesIO()
    foto.save(salida, "WEBP", quality=CALIDAD_WEBP, method=6)  # sin exif: no se pasa a save()
    return salida.getvalue()
