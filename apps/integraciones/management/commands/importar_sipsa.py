"""Importa precios de referencia SIPSA (DANE) (RF-07): de un CSV o del servicio web SOAP.

Uso:
    python manage.py importar_sipsa archivo.csv [--codificacion latin-1]
    python manage.py importar_sipsa --servicio-web [--ciudad ARMENIA] [--dias 7] [--crear-faltantes]

El servicio web (promediosSipsaCiudad) trae ~120 MB y tarda ~1 min; el DANE publica después de
las 2 p. m. Formato y pasos: docs/integraciones/sipsa.md.
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.integraciones.clients.sipsa import (
    ArchivoSipsaInvalidoError,
    ClienteSipsa,
    SipsaNoDisponibleError,
    leer_csv_sipsa,
)
from apps.integraciones.services import importar_referencias


class Command(BaseCommand):
    help = "Importa precios de referencia SIPSA desde un CSV del DANE o desde su servicio web."

    def add_arguments(self, parser):
        parser.add_argument("archivo", type=Path, nargs="?")
        parser.add_argument("--codificacion", default="utf-8-sig")
        parser.add_argument(
            "--servicio-web", action="store_true", help="Consulta el SOAP del DANE."
        )
        parser.add_argument("--ciudad", default="ARMENIA", help="Ciudad de SIPSA (servicio web).")
        parser.add_argument("--dias", type=int, default=7, help="Días recientes que se importan.")
        parser.add_argument(
            "--crear-faltantes",
            action="store_true",
            help="Crea en el catálogo los frescos que falten (sin marca, 1 kg).",
        )

    def handle(self, *args, **opciones):
        if opciones["servicio_web"]:
            precios, errores = self._del_servicio(opciones), []
        elif opciones["archivo"]:
            precios, errores = self._del_archivo(opciones["archivo"], opciones["codificacion"])
        else:
            raise CommandError("Indique un archivo CSV o use --servicio-web.")
        for linea, error in errores:
            self.stderr.write(f"Línea {linea}: {error}")
        resumen = importar_referencias(precios, crear_faltantes=opciones["crear_faltantes"])
        self.stdout.write(
            self.style.SUCCESS(
                f"SIPSA: {resumen.creados} nuevos, {resumen.actualizados} actualizados, "
                f"{len(errores)} filas con error."
            )
        )
        if resumen.productos_creados:
            creados = ", ".join(sorted(set(resumen.productos_creados)))
            self.stdout.write(f"Productos creados en el catálogo: {creados}")
        if resumen.sin_producto:
            faltantes = ", ".join(sorted(set(resumen.sin_producto)))
            self.stdout.write(f"Sin producto en el catálogo (no se importaron): {faltantes}")

    def _del_archivo(self, ruta: Path, codificacion: str):
        if not ruta.is_file():
            raise CommandError(f"No existe el archivo {ruta}.")
        try:
            with ruta.open(encoding=codificacion, newline="") as f:
                lectura = leer_csv_sipsa(f)
        except (ArchivoSipsaInvalidoError, UnicodeDecodeError) as exc:
            raise CommandError(str(exc)) from exc
        return lectura.precios, lectura.errores

    def _del_servicio(self, opciones):
        self.stdout.write("Consultando SIPSA (DANE); puede tardar un par de minutos…")
        try:
            return ClienteSipsa().promedios_ciudad(ciudad=opciones["ciudad"], dias=opciones["dias"])
        except SipsaNoDisponibleError as exc:
            raise CommandError(f"SIPSA no disponible: {exc}") from exc
