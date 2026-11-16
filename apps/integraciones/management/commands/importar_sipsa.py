"""Importa un CSV de SIPSA (DANE) descargado a mano (RF-07).

Uso: python manage.py importar_sipsa archivo.csv [--codificacion latin-1]
Formato y pasos de descarga: docs/integraciones/sipsa.md.
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.integraciones.clients.sipsa import ArchivoSipsaInvalidoError, leer_csv_sipsa
from apps.integraciones.services import importar_referencias


class Command(BaseCommand):
    help = "Importa precios de referencia SIPSA desde un CSV descargado del DANE."

    def add_arguments(self, parser):
        parser.add_argument("archivo", type=Path)
        parser.add_argument("--codificacion", default="utf-8-sig")

    def handle(self, *args, **opciones):
        ruta: Path = opciones["archivo"]
        if not ruta.is_file():
            raise CommandError(f"No existe el archivo {ruta}.")
        try:
            with ruta.open(encoding=opciones["codificacion"], newline="") as f:
                lectura = leer_csv_sipsa(f)
        except (ArchivoSipsaInvalidoError, UnicodeDecodeError) as exc:
            raise CommandError(str(exc)) from exc
        for linea, error in lectura.errores:
            self.stderr.write(f"Línea {linea}: {error}")
        resumen = importar_referencias(lectura.precios)
        self.stdout.write(
            self.style.SUCCESS(
                f"SIPSA: {resumen.creados} nuevos, {resumen.actualizados} actualizados, "
                f"{len(lectura.errores)} filas con error."
            )
        )
        if resumen.sin_producto:
            faltantes = ", ".join(sorted(set(resumen.sin_producto)))
            self.stdout.write(f"Sin producto en el catálogo (no se importaron): {faltantes}")
