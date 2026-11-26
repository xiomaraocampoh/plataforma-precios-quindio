"""Importa una carpeta de fotos a los productos del catálogo (ADR-0024).

    python manage.py cargar_fotos <carpeta> [--dry-run] [--reemplazar]

El nombre del archivo dice a qué producto va, sin extensión: su código de barras (8 a 14 dígitos),
su id, o su nombre con la marca («arroz-blanco_diana.jpg»). Cada foto se valida, se recorta cuadrada
y se reduce igual que al subirla desde el panel. Lo que no encaja o no es una imagen válida se
informa y no detiene el resto. No pisa una foto existente salvo con --reemplazar.
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.catalogo import selectors, services
from apps.catalogo.domain.fotos import FotoInvalidaError

EXTENSIONES = {".jpg", ".jpeg", ".png", ".webp"}


def _buscar(stem: str):
    """Los productos públicos que corresponden al nombre del archivo (sin extensión)."""
    if stem.isdigit() and 8 <= len(stem) <= 14:  # código de barras
        return list(selectors.productos_por_codigo(stem))
    if stem.isdigit():  # id del producto
        producto = selectors.obtener_producto(int(stem))
        return [producto] if producto else []
    return selectors.productos_por_nombre_de_archivo(stem)


class Command(BaseCommand):
    help = "Importa fotos de una carpeta; el nombre del archivo indica el producto."

    def add_arguments(self, parser):
        parser.add_argument("carpeta", help="Carpeta con las imágenes (.jpg, .png o .webp).")
        parser.add_argument("--dry-run", action="store_true", help="Solo informa; no guarda.")
        parser.add_argument(
            "--reemplazar", action="store_true", help="Reemplaza la foto que ya tenga el producto."
        )

    def handle(self, *args, carpeta, dry_run, reemplazar, **opciones):
        ruta = Path(carpeta)
        if not ruta.is_dir():
            raise CommandError(f"La carpeta {carpeta} no existe.")
        archivos = sorted(
            a for a in ruta.iterdir() if a.is_file() and a.suffix.lower() in EXTENSIONES
        )
        cargadas = omitidas = sin_producto = invalidas = ambiguas = 0
        for archivo in archivos:
            productos = _buscar(archivo.stem)
            if not productos:
                sin_producto += 1
                self.stdout.write(f"✗ {archivo.name}: sin producto que coincida.")
                continue
            if len(productos) > 1:
                ambiguas += 1
                nombres = ", ".join(str(p) for p in productos[:3])
                self.stdout.write(f"✗ {archivo.name}: ambiguo, coincide con varios ({nombres}).")
                continue
            producto = productos[0]
            if producto.foto_version and not reemplazar:
                omitidas += 1
                self.stdout.write(f"· {archivo.name}: {producto} ya tiene foto (usa --reemplazar).")
                continue
            try:
                miniatura = services.preparar_foto(archivo.read_bytes())
            except FotoInvalidaError as exc:
                invalidas += 1
                self.stdout.write(f"✗ {archivo.name}: {exc}")
                continue
            if not dry_run:
                services.guardar_foto(producto, miniatura)
            cargadas += 1
            self.stdout.write(f"✓ {archivo.name} → {producto}")
        plural = "foto" if cargadas == 1 else "fotos"
        if dry_run:
            verbo = "se cargaría" if cargadas == 1 else "se cargarían"
            titulo = "Simulación (no se guardó nada): "
        else:
            verbo = "cargada" if cargadas == 1 else "cargadas"
            titulo = ""
        self.stdout.write(
            f"{titulo}{cargadas} {plural} {verbo}; {sin_producto} sin producto, "
            f"{ambiguas} ambiguas, {invalidas} inválidas, {omitidas} omitidas."
        )
