"""Reglas de la foto de un producto (RF-06): qué se acepta y cómo se recorta.

Capa de dominio: Python puro, sin Django ni Pillow. Decide si una subida es válida y qué región
recortar para dejarla cuadrada; el procesamiento de la imagen vive en `catalogo/imagenes.py`.

Neutralidad (EC-06): todas las fotos salen del mismo tamaño y forma (cuadradas), así ninguna
marca ni tienda destaca por el encuadre. Peso (EC-01): miniaturas pequeñas para 3G.
"""

FORMATOS_ACEPTADOS = frozenset({"JPEG", "PNG", "WEBP"})
MAX_BYTES_SUBIDA = 5 * 1024 * 1024  # 5 MB: lo que se acepta subir; lo guardado pesa mucho menos
MAX_PIXELES = 40_000_000  # protege de «bombas de descompresión» (pesan poco, ocupan mucha memoria)
MIN_LADO = 200  # por debajo de esto, la miniatura se vería borrosa
LADO_MINIATURA = 480  # nítida en pantallas densas de celular y liviana en 3G


class FotoInvalidaError(ValueError):
    """La foto no cumple las reglas. El mensaje es una oración lista para mostrar en el panel."""


def validar_subida(*, formato: str | None, ancho: int, alto: int, tamano: int) -> None:
    """Lanza FotoInvalidaError si la subida no sirve; si no, no devuelve nada."""
    if formato not in FORMATOS_ACEPTADOS:
        raise FotoInvalidaError("La foto debe ser un archivo JPG, PNG o WebP.")
    if tamano <= 0:
        raise FotoInvalidaError("El archivo está vacío.")
    if tamano > MAX_BYTES_SUBIDA:
        raise FotoInvalidaError(f"El archivo pesa más de {MAX_BYTES_SUBIDA // (1024 * 1024)} MB.")
    if ancho <= 0 or alto <= 0:
        raise FotoInvalidaError("No se pudieron leer las dimensiones de la foto.")
    if ancho * alto > MAX_PIXELES:
        millones = MAX_PIXELES // 1_000_000
        raise FotoInvalidaError(
            f"La foto es demasiado grande: usa una de menos de {millones} millones de píxeles."
        )
    if min(ancho, alto) < MIN_LADO:
        raise FotoInvalidaError(
            f"La foto es muy pequeña: debe medir al menos {MIN_LADO} px por lado."
        )


def recorte_cuadrado(ancho: int, alto: int) -> tuple[int, int, int, int]:
    """(izquierda, arriba, derecha, abajo) del mayor cuadrado centrado dentro de la imagen."""
    if ancho <= 0 or alto <= 0:
        raise ValueError("Las dimensiones deben ser positivas.")
    lado = min(ancho, alto)
    izquierda = (ancho - lado) // 2
    arriba = (alto - lado) // 2
    return izquierda, arriba, izquierda + lado, arriba + lado
