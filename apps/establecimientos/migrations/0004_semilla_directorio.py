"""Siembra de prueba: establecimientos aprobados de data/demo/establecimientos.csv (ADR-0023).

- Solo si DEBUG=True o SEMBRAR_DATOS_PRUEBA=True (en producción no siembra por defecto).
- Idempotente por nombre y municipio. El local sugerido (pendiente) necesita un autor: lo siembra
  `precios.0004_semilla_precios_prueba`.
- Lógica en `apps/establecimientos/semilla.py`, con modelos históricos.
- Reversa: borra los locales sembrados que ningún precio usa.
"""

from django.db import migrations

from apps.establecimientos import semilla
from core.semilla import Resumen, avisar, directorio_por_defecto, sembrar_datos_activo


def sembrar(apps, schema_editor):
    if not sembrar_datos_activo():
        return
    resumen = Resumen()
    semilla.sembrar(apps, directorio=directorio_por_defecto(), resumen=resumen)
    avisar(f"Directorio de prueba: {resumen.texto()}.")


def revertir(apps, schema_editor):
    if sembrar_datos_activo():
        semilla.revertir(apps, directorio=directorio_por_defecto())


class Migration(migrations.Migration):
    dependencies = [("establecimientos", "0003_tipos_discount_y_plaza")]

    operations = [migrations.RunPython(sembrar, revertir)]
