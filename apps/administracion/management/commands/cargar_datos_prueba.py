"""Carga los datos de prueba de data/demo/ (catálogo, directorio, precios y escenarios).

Uso: python manage.py cargar_datos_prueba [--limpiar] [--solo-catalogo] [--directorio RUTA]

- Idempotente: correrlo dos veces no duplica nada.
- --limpiar: borra antes los datos de prueba (lo que usen datos reales se conserva) y vuelve a
  cargar.
- --solo-catalogo: marcas, categorías, productos, presentaciones y establecimientos; sin precios.
- Los autores son las cuentas de crear_cuentas_prueba; si no existen se crean SIN contraseña
  utilizable (para ingresar, corra crear_cuentas_prueba con CUENTAS_PRUEBA_PASSWORD).

Son DATOS DE PRUEBA: pueden no coincidir con los precios actuales (ver data/demo/README.md).
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.administracion.services import datos_prueba

ETIQUETAS = [
    ("marcas", "Marcas"),
    ("categorias", "Categorías"),
    ("productos", "Productos"),
    ("presentaciones", "Presentaciones"),
    ("establecimientos", "Establecimientos"),
    ("precios", "Precios"),
    ("en_revision", "  de ellos en revisión (anómalos)"),
    ("sigue_igual", "«Sigue igual»"),
    ("denuncias", "Denuncias abiertas"),
    ("solicitudes", "Solicitudes de producto"),
    ("sugeridos", "Establecimientos sugeridos pendientes"),
]


class Command(BaseCommand):
    help = "Carga los datos de prueba de data/demo/ (idempotente)."

    def add_arguments(self, parser):
        parser.add_argument("--limpiar", action="store_true", help="Borra antes los de prueba.")
        parser.add_argument(
            "--solo-catalogo", action="store_true", help="Sin precios ni escenarios."
        )
        parser.add_argument("--directorio", type=Path, default=None, help="Otra carpeta de CSV.")

    def handle(self, *args, **opciones):
        directorio = opciones["directorio"]
        try:
            if opciones["limpiar"]:
                borrados = datos_prueba.limpiar(directorio=directorio)
                texto = ", ".join(f"{n} {clave}" for clave, n in borrados.items())
                self.stdout.write(f"Datos de prueba borrados: {texto}.")
            resumen = datos_prueba.cargar(
                directorio=directorio, solo_catalogo=opciones["solo_catalogo"]
            )
        except datos_prueba.DatosDePruebaInvalidosError as exc:
            raise CommandError(str(exc)) from exc
        for aviso in resumen.avisos:
            self.stdout.write(self.style.WARNING(aviso))
        self.stdout.write("Resumen (total en el conjunto / nuevos en esta corrida):")
        for clave, etiqueta in ETIQUETAS:
            if clave in resumen.totales:
                total, nuevos = resumen.totales[clave], resumen.nuevos[clave]
                self.stdout.write(f"  {etiqueta}: {total} ({nuevos} nuevos)")
        self.stdout.write(
            self.style.SUCCESS("Listo. Datos de prueba; pueden no coincidir con precios actuales.")
        )
