"""Renueva las fechas de los precios de prueba (es_demo=True) según su antigüedad relativa.

Uso: python manage.py refrescar_precios_prueba

precios.csv guarda «hace N días»; `migrate` y `cargar_datos_prueba` fechan cada precio desde el
momento de la carga. Con los días todo envejece y termina vencido (EC-02). Este comando vuelve a
poner cada precio a la misma distancia de hoy: los «hace 2 días» vuelven a estar a 2 días y los
escenarios vencidos (8, 4 y 31 días) siguen justo fuera de su ventana. Los «Sigue igual» de prueba
pasan a hoy. Solo toca datos de prueba; los precios reales no se mueven. Idempotente.
"""

from django.core.management.base import BaseCommand, CommandError

from apps.administracion.services import datos_prueba


class Command(BaseCommand):
    help = "Renueva las fechas de los precios de prueba (es_demo) según su antigüedad relativa."

    def handle(self, *args, **opciones):
        try:
            movidos = datos_prueba.refrescar()
        except datos_prueba.DatosDePruebaInvalidosError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"Listo: {movidos['precios']} precios de prueba y "
                f"{movidos['confirmaciones']} «Sigue igual» con fechas renovadas."
            )
        )
